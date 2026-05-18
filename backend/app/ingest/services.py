from datetime import datetime, timedelta, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ingest.grade_map import map_grade
from app.ingest.schemas import (
    IngestErrorRow,
    IngestRequest,
    IngestResponse,
    PriceIngestRow,
)
from app.items.models import Item, ItemCategory, ItemGrade
from app.prices.schemas import PricePointCreate
from app.prices.services import add_price_point


async def match_or_create_item(
    session: AsyncSession, name: str, grade: ItemGrade
) -> tuple[Item, bool]:
    """Find Item by exact name+grade, create with category=OTHER if missing.

    Returns (item, created) where created=True if a new Item was inserted.
    """
    query = select(Item).where(Item.name == name, Item.grade == grade)
    result = await session.exec(query)
    item = result.first()
    if item is not None:
        return item, False

    item = Item(name=name, grade=grade, category=ItemCategory.OTHER)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item, True


def _normalize_ts(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


def _is_future(ts: datetime, tolerance: timedelta = timedelta(hours=1)) -> bool:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return ts > now + tolerance


async def _process_row(
    session: AsyncSession, idx: int, row: PriceIngestRow
) -> tuple[bool, bool, IngestErrorRow | None]:
    """Returns (accepted, created, error)."""
    grade = map_grade(row.grade)
    if grade is None:
        return (
            False,
            False,
            IngestErrorRow(row_index=idx, reason=f"unknown game grade {row.grade}"),
        )

    ts = _normalize_ts(row.ts)
    if _is_future(ts):
        return False, False, IngestErrorRow(row_index=idx, reason="ts is in the future")

    try:
        item, created = await match_or_create_item(session, name=row.name, grade=grade)
    except Exception as e:
        return (
            False,
            False,
            IngestErrorRow(row_index=idx, reason=f"item match failed: {e}"),
        )

    try:
        await add_price_point(
            session,
            item.id,
            PricePointCreate(source=row.source, price=row.price, captured_at=ts),
        )
    except Exception as e:
        await session.rollback()
        return (
            False,
            created,
            IngestErrorRow(row_index=idx, reason=f"price_point failed: {e}"),
        )

    return True, created, None


async def bulk_ingest(session: AsyncSession, request: IngestRequest) -> IngestResponse:
    accepted = 0
    auto_created = 0
    skipped = 0
    errors: list[IngestErrorRow] = []

    for idx, row in enumerate(request.rows):
        ok, created, err = await _process_row(session, idx, row)
        if ok:
            accepted += 1
            if created:
                auto_created += 1
        else:
            skipped += 1
            if err is not None:
                errors.append(err)

    return IngestResponse(
        accepted=accepted,
        auto_created=auto_created,
        skipped=skipped,
        errors=errors,
    )
