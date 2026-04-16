from datetime import datetime, timezone
from enum import StrEnum

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, and_, select

from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item
from app.prices.models import PricePoint
from app.prices.schemas import PriceBucketRead, PricePointRead

router = APIRouter(prefix="/items", tags=["prices"])


class Interval(StrEnum):
    RAW = "raw"
    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


INTERVAL_SECONDS: dict[Interval, int] = {
    Interval.FIVE_MINUTES: 300,
    Interval.ONE_HOUR: 3600,
    Interval.ONE_DAY: 86400,
}


@router.get(
    "/{item_id}/price-history",
    response_model=list[PricePointRead] | list[PriceBucketRead],
)
def read_item_price_history(
    item_id: int,
    source: str = Query(min_length=1, max_length=40),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    interval: Interval = Query(default=Interval.RAW),
    session: Session = Depends(get_session),
) -> list[PricePointRead] | list[PriceBucketRead]:
    if session.get(Item, item_id) is None:
        raise NotFoundError("Item not found")

    query = select(PricePoint).where(
        and_(PricePoint.item_id == item_id, PricePoint.source == source)
    )
    if from_ts is not None:
        query = query.where(PricePoint.captured_at >= from_ts)
    if to_ts is not None:
        query = query.where(PricePoint.captured_at <= to_ts)

    rows = session.exec(query.order_by(PricePoint.captured_at)).all()

    if interval == Interval.RAW:
        return [
            PricePointRead(
                item_id=row.item_id,
                source=row.source,
                price=row.price,
                captured_at=row.captured_at,
            )
            for row in rows
        ]

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
