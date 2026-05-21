from datetime import datetime, timezone
from sqlalchemy import update
from sqlmodel import and_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.exceptions import NotFoundError
from app.items.models import Item
from app.prices.models import PricePoint, utcnow
from app.prices.schemas import PriceBucketRead, PricePointCreate, PricePointRead


async def get_item_price_history(
    session: AsyncSession,
    item_id: int,
    source: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    interval: str = "raw",
) -> list[PricePointRead] | list[PriceBucketRead]:
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    def to_naive(dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

    query = select(PricePoint).where(
        and_(PricePoint.item_id == item_id, PricePoint.source == source)
    )
    if from_ts is not None:
        query = query.where(PricePoint.captured_at >= to_naive(from_ts))
    if to_ts is not None:
        query = query.where(PricePoint.captured_at <= to_naive(to_ts))

    result = await session.exec(query.order_by(PricePoint.captured_at))
    rows = result.all()

    if interval == "raw":
        return [
            PricePointRead(
                item_id=row.item_id,
                source=row.source,
                price=row.price,
                captured_at=row.captured_at,
            )
            for row in rows
        ]

    # Map intervals to seconds
    INTERVAL_SECONDS: dict[str, int] = {
        "5m": 300,
        "1h": 3600,
        "1d": 86400,
    }

    seconds = INTERVAL_SECONDS[interval]
    buckets: dict[datetime, dict[str, int]] = {}

    for row in rows:
        captured = row.captured_at
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)

        bucket_epoch = int(captured.timestamp()) // seconds * seconds
        bucket_start = datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)

        bucket = buckets.get(bucket_start)
        if bucket is None:
            buckets[bucket_start] = {
                "min_price": row.price,
                "max_price": row.price,
                "sum_price": row.price,
                "count": 1,
                "last_price": row.price,
            }
            continue

        bucket["min_price"] = min(bucket["min_price"], row.price)
        bucket["max_price"] = max(bucket["max_price"], row.price)
        bucket["sum_price"] += row.price
        bucket["count"] += 1
        bucket["last_price"] = row.price

    return [
        PriceBucketRead(
            bucket_start=bucket_start,
            min_price=values["min_price"],
            max_price=values["max_price"],
            avg_price=values["sum_price"] / values["count"],
            last_price=values["last_price"],
        )
        for bucket_start, values in sorted(buckets.items(), key=lambda x: x[0])
    ]


async def add_price_point(
    session: AsyncSession,
    item_id: int,
    data: PricePointCreate,
) -> PricePoint:
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    # Strip timezone info — DB column is TIMESTAMP WITHOUT TIME ZONE (UTC assumed)
    captured_at = data.captured_at
    if captured_at.tzinfo is not None:
        captured_at = captured_at.astimezone(timezone.utc).replace(tzinfo=None)

    point = PricePoint(
        item_id=item_id,
        source=data.source,
        price=data.price,
        captured_at=captured_at,
    )
    session.add(point)

    # Atomic guarded update: only overwrite current_price/last_price_at if the
    # incoming captured_at is newer-or-equal to the persisted last_price_at.
    # The WHERE clause runs inside the DB so concurrent writers can't race a
    # check-then-set. On exact ties the last-arriving statement wins (DB row
    # lock serializes them); originally last-write-wins on ties too.
    await session.execute(
        update(Item)
        .where(Item.id == item_id)
        .where((Item.last_price_at.is_(None)) | (Item.last_price_at <= captured_at))
        .values(
            current_price=data.price,
            last_price_at=captured_at,
            updated_at=utcnow(),
        )
    )

    await session.commit()
    await session.refresh(point)
    return point
