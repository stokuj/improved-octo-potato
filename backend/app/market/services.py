import math

from sqlalchemy import func, literal_column, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.market.csv_format import (
    CsvFormatError,
    ListingRow,
    MarketRow,
    ParsedFile,
    RowError,
    parse_csv,
)
from app.core.errors import NotFoundError
from app.market.models import Item, Listing, MarketDay
from app.imports.schemas import ImportFileResult, ImportRowError, failed
from app.market.schemas import (
    ListingRead,
    ListingsRead,
    MarketDayRead,
    MarketItemRead,
)

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ERRORS = 100
CHUNK_ROWS = 2_000  # 9 columns x 2000 stays under asyncpg's 32767 bind params
NAME_MAX = 120
GRADE_CONFLICT = "name already used by another grade"
MIN_REAL_STACK = 10
REAL_STACK_SHARE = 0.002  # of the average daily volume, a fraction


def min_stack(avg_volume: float | None) -> int:
    """Smallest stack that counts as a real offer; smaller ones are likely bait."""
    return max(MIN_REAL_STACK, math.ceil((avg_volume or 0) * REAL_STACK_SHARE))


async def resolve_items(
    session: AsyncSession,
    market_keys: dict[str, tuple[int, int]],
    listing_names: set[str],
) -> tuple[dict[str, int], dict[str, str]]:
    """Map item names to ids, creating/updating items; returns (ids, errors by name)."""
    errors = {
        n: f"item name longer than {NAME_MAX}"
        for n in {*market_keys, *listing_names}
        if len(n) > NAME_MAX
    }
    names = {*market_keys, *listing_names} - errors.keys()
    keys = {k for n, k in market_keys.items() if n in names}
    by_name = (
        {
            i.name: i
            for i in (
                await session.exec(select(Item).where(col(Item.name).in_(names)))
            ).all()
        }
        if names
        else {}
    )
    by_key = (
        {
            (i.item_type, i.item_grade): i
            for i in (
                await session.exec(
                    select(Item).where(
                        tuple_(Item.item_type, Item.item_grade).in_(keys)
                    )
                )
            ).all()
        }
        if keys
        else {}
    )

    # Every resolved input name -> its item; kept apart from by_name so a rename
    # inside one file still maps the old name's rows to the same item.
    resolved: dict[str, Item] = {}
    for name, key in market_keys.items():
        if name not in names:
            continue
        item = by_key.get(key)
        if item is not None:
            if item.name != name:
                if name in by_name:  # another item already owns this name
                    errors[name] = GRADE_CONFLICT
                    continue
                by_name.pop(item.name, None)
                item.name = name
        else:
            item = by_name.get(name)
            if item is None:
                item = Item(name=name, item_type=key[0], item_grade=key[1])
            elif item.item_type is None:
                item.item_type, item.item_grade = key
            else:
                errors[name] = GRADE_CONFLICT
                continue
            by_key[key] = item
        by_name[name] = resolved[name] = item
        session.add(item)

    for name in listing_names & names:
        if name not in resolved and name not in errors:
            if name not in by_name:
                by_name[name] = Item(name=name)
                session.add(by_name[name])
            resolved[name] = by_name[name]

    await session.flush()
    ids = {n: i.id for n, i in resolved.items() if n not in errors}
    return ids, errors


def _chunks(rows: list[dict]) -> list[list[dict]]:
    return [rows[i : i + CHUNK_ROWS] for i in range(0, len(rows), CHUNK_ROWS)]


async def _import_market(
    session: AsyncSession, parsed: ParsedFile, errors: list[RowError]
) -> tuple[int, int, int]:
    keys: dict[str, tuple[int, int]] = {}
    for r in parsed.market:
        keys.setdefault(r.item, (r.item_type, r.item_grade))
    ids, bad = await resolve_items(session, keys, set())

    best: dict[tuple[int, object], MarketRow] = {}
    valid = 0
    for r in parsed.market:
        reason = bad.get(r.item)
        if reason is None and keys[r.item] != (r.item_type, r.item_grade):
            reason = GRADE_CONFLICT  # same name, second grade within one file
        if reason is not None:
            errors.append(RowError(r.line, reason))
            continue
        valid += 1
        k = (ids[r.item], r.day)
        if k not in best or r.captured_at > best[k].captured_at:
            best[k] = r

    values = [
        {
            "item_id": item_id,
            "day": day,
            "daily_avg": r.daily_avg,
            "weekly_avg": r.weekly_avg,
            "min": r.min,
            "max": r.max,
            "volume": r.volume,
            "scan_id": r.scan_id,
            "captured_at": r.captured_at,
        }
        for (item_id, day), r in best.items()
    ]
    inserted = updated = 0
    for chunk in _chunks(values):
        stmt = pg_insert(MarketDay).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["item_id", "day"],
            set_={c: stmt.excluded[c] for c in chunk[0] if c not in ("item_id", "day")},
            where=col(MarketDay.captured_at) < stmt.excluded.captured_at,
        ).returning(literal_column("(xmax = 0)"))
        flags = (await session.exec(stmt)).scalars().all()  # type: ignore[call-overload]
        inserted += sum(flags)
        updated += len(flags) - sum(flags)
    newest: dict[int, MarketRow] = {}  # item id -> its newest row with a category
    for (item_id, _), r in best.items():
        if r.category and (
            item_id not in newest or r.captured_at > newest[item_id].captured_at
        ):
            newest[item_id] = r
    for item_id, r in newest.items():
        await session.exec(  # type: ignore[call-overload]
            update(Item).where(col(Item.id) == item_id).values(category=r.category)
        )
    skipped = parsed.skipped + valid - inserted - updated
    return inserted, updated, skipped


async def _import_listings(
    session: AsyncSession, parsed: ParsedFile, errors: list[RowError]
) -> tuple[int, int, int]:
    keys: dict[str, tuple[int, int]] = {}
    for r in parsed.listings:
        if r.item_type is not None and r.item_grade is not None:
            keys.setdefault(r.item, (r.item_type, r.item_grade))
    names = {r.item for r in parsed.listings if r.item_type is None}
    ids, bad = await resolve_items(session, keys, names)
    rows: list[ListingRow] = []
    for r in parsed.listings:
        reason = bad.get(r.item)
        if reason is None and r.item_type is not None:
            if keys[r.item] != (r.item_type, r.item_grade):
                reason = GRADE_CONFLICT  # same name, second grade within one file
        if reason is not None:
            errors.append(RowError(r.line, reason))
        else:
            rows.append(r)
    values = [
        {
            "item_id": ids[r.item],
            "scan_id": r.scan_id,
            "rank": r.rank,
            "captured_at": r.captured_at,
            "status": r.status,
            "unit_price": r.unit_price,
            "listing_price": r.listing_price,
            "stack": r.stack,
        }
        for r in rows
    ]
    inserted = 0
    for chunk in _chunks(values):
        stmt = (
            pg_insert(Listing)
            .values(chunk)
            .on_conflict_do_nothing()
            .returning(literal_column("1"))
        )
        inserted += len((await session.exec(stmt)).all())  # type: ignore[call-overload]
    return inserted, 0, len(rows) - inserted


async def import_csv(
    session: AsyncSession, filename: str, data: bytes
) -> ImportFileResult:
    if len(data) > MAX_FILE_BYTES:
        return failed(filename, None, 0, "file larger than 50 MB")
    try:
        parsed = parse_csv(data)
    except CsvFormatError as e:
        return failed(filename, None, 0, str(e))

    errors = list(parsed.errors)
    importer = _import_market if parsed.kind == "market" else _import_listings
    try:
        inserted, updated, skipped = await importer(session, parsed, errors)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        return failed(
            filename, parsed.kind, parsed.rows, f"database error: {type(e).__name__}"
        )

    errors.sort(key=lambda e: e.line)
    return ImportFileResult(
        filename=filename,
        kind=parsed.kind,
        rows=parsed.rows,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        error_count=len(errors),
        errors=[
            ImportRowError(line=e.line, reason=e.reason) for e in errors[:MAX_ERRORS]
        ],
    )


async def _get_item(session: AsyncSession, item_id: int) -> Item:
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")
    return item


# Mean volume of the 7 days before each item's last market day.
_VOL_CTE = """
    last_day AS (SELECT item_id, max(day) AS day FROM market_day GROUP BY item_id),
    vol AS (
        SELECT d.item_id, avg(m.volume) AS avg_volume
        FROM last_day d
        JOIN market_day m
          ON m.item_id = d.item_id AND m.day BETWEEN d.day - 7 AND d.day - 1
        GROUP BY d.item_id
    )
"""

_ITEMS_SQL = text(
    f"""
    WITH {_VOL_CTE},
    latest AS (SELECT item_id, max(scan_id) AS scan_id FROM listing GROUP BY item_id),
    tracked AS (SELECT item_id FROM last_day UNION SELECT item_id FROM latest)
    SELECT i.id, i.name, i.item_type, i.item_grade, i.category,
           d.day AS last_day, v.avg_volume, max(l.captured_at) AS scan_at,
           min(l.unit_price) FILTER (
             WHERE l.status = 'ok'
               AND l.stack >= greatest(:floor, ceil(coalesce(v.avg_volume, 0) * :share))
           ) AS cheapest_real
    FROM tracked t
    JOIN item i ON i.id = t.item_id
    LEFT JOIN last_day d ON d.item_id = i.id
    LEFT JOIN vol v ON v.item_id = i.id
    LEFT JOIN latest s ON s.item_id = i.id
    LEFT JOIN listing l ON l.item_id = i.id AND l.scan_id = s.scan_id
    GROUP BY i.id, d.day, v.avg_volume
    ORDER BY i.name
    """
)

_ITEM_VOL_SQL = text(f"WITH {_VOL_CTE} SELECT avg_volume FROM vol WHERE item_id = :id")


async def list_items(session: AsyncSession) -> list[MarketItemRead]:
    params = {"floor": MIN_REAL_STACK, "share": REAL_STACK_SHARE}
    rows = (await session.exec(_ITEMS_SQL, params=params)).mappings().all()  # type: ignore[call-overload]
    return [
        MarketItemRead(
            **{k: v for k, v in r.items() if k != "avg_volume"},
            min_stack=min_stack(
                float(r["avg_volume"]) if r["avg_volume"] is not None else None
            ),
        )
        for r in rows
    ]


async def get_days(
    session: AsyncSession, item_id: int, days: int
) -> list[MarketDayRead]:
    await _get_item(session, item_id)
    rows = await session.exec(
        select(MarketDay)
        .where(MarketDay.item_id == item_id)
        .order_by(col(MarketDay.day).desc())
        .limit(days)
    )
    return [
        MarketDayRead.model_validate(r, from_attributes=True)
        for r in reversed(rows.all())
    ]


async def get_latest_listings(session: AsyncSession, item_id: int) -> ListingsRead:
    await _get_item(session, item_id)
    newest = (
        select(func.max(Listing.scan_id))
        .where(Listing.item_id == item_id)
        .scalar_subquery()
    )
    rows = (
        await session.exec(
            select(Listing)
            .where(Listing.item_id == item_id, Listing.scan_id == newest)
            .order_by(Listing.rank)
        )
    ).all()
    avg = (await session.exec(_ITEM_VOL_SQL, params={"id": item_id})).scalar()  # type: ignore[call-overload]
    floor = min_stack(float(avg) if avg is not None else None)
    return ListingsRead(
        scan_id=rows[0].scan_id if rows else None,
        captured_at=rows[0].captured_at if rows else None,
        min_stack=floor,
        listings=[
            ListingRead(
                **r.model_dump(exclude={"item_id"}),
                tiny=r.status == "ok" and r.stack is not None and r.stack < floor,
            )
            for r in rows
        ],
    )
