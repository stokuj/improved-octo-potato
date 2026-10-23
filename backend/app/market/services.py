from sqlalchemy import func, literal_column, text, tuple_
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
    MarketDayRead,
    MarketItemRead,
    SummaryRow,
)

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ERRORS = 100
CHUNK_ROWS = 2_000  # 9 columns x 2000 stays under asyncpg's 32767 bind params
NAME_MAX = 120
GRADE_CONFLICT = "name already used by another grade"


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
    skipped = parsed.skipped + valid - inserted - updated
    return inserted, updated, skipped


async def _import_listings(
    session: AsyncSession, parsed: ParsedFile, errors: list[RowError]
) -> tuple[int, int, int]:
    ids, bad = await resolve_items(session, {}, {r.item for r in parsed.listings})
    rows: list[ListingRow] = []
    for r in parsed.listings:
        if r.item in bad:
            errors.append(RowError(r.line, bad[r.item]))
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


async def list_items(session: AsyncSession) -> list[MarketItemRead]:
    last_day = (
        select(func.max(MarketDay.day))
        .where(MarketDay.item_id == Item.id)
        .scalar_subquery()
    )
    has_data = select(MarketDay.item_id).where(
        MarketDay.item_id == Item.id
    ).exists() | (select(Listing.item_id).where(Listing.item_id == Item.id).exists())
    rows = await session.exec(
        select(Item, last_day).where(has_data).order_by(Item.name)  # type: ignore[call-overload]
    )
    return [
        MarketItemRead(
            id=i.id,
            name=i.name,
            item_type=i.item_type,
            item_grade=i.item_grade,
            last_day=d,
        )
        for i, d in rows.all()
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


async def get_latest_listings(session: AsyncSession, item_id: int) -> list[ListingRead]:
    await _get_item(session, item_id)
    newest = (
        select(func.max(Listing.scan_id))
        .where(Listing.item_id == item_id)
        .scalar_subquery()
    )
    rows = await session.exec(
        select(Listing)
        .where(Listing.item_id == item_id, Listing.scan_id == newest)
        .order_by(Listing.rank)
    )
    return [ListingRead.model_validate(r, from_attributes=True) for r in rows.all()]


_SUMMARY_SQL = text(
    """
    WITH latest AS (
        SELECT item_id, max(day) AS day FROM market_day GROUP BY item_id
    )
    SELECT i.id AS item_id, i.name, l.day,
           t.daily_avg AS today_avg, t.volume AS sold_today,
           p.weekly_avg AS avg_7d,
           (SELECT avg(w.volume) FROM market_day w
             WHERE w.item_id = l.item_id
               AND w.day BETWEEN l.day - 7 AND l.day - 1) AS avg_daily_volume
    FROM latest l
    JOIN item i ON i.id = l.item_id
    JOIN market_day t ON t.item_id = l.item_id AND t.day = l.day
    LEFT JOIN market_day p ON p.item_id = l.item_id AND p.day = l.day - 1
    ORDER BY i.name
    """
)


async def get_summary(session: AsyncSession) -> list[SummaryRow]:
    rows = (await session.exec(_SUMMARY_SQL)).mappings().all()  # type: ignore[call-overload]
    return [
        SummaryRow(
            **r,
            change_pct=round((r["today_avg"] - r["avg_7d"]) / r["avg_7d"], 4)
            if r["avg_7d"]
            else None,
        )
        for r in rows
    ]
