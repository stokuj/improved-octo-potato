from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import get_async_session
from app.prices.schemas import PriceBucketRead, PricePointRead
from app.prices.services import get_item_price_history

router = APIRouter(prefix="/items", tags=["prices"])


class Interval(StrEnum):
    RAW = "raw"
    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


@router.get(
    "/{item_id}/price-history",
    response_model=list[PricePointRead] | list[PriceBucketRead],
)
async def read_item_price_history(
    item_id: int,
    source: str = Query(min_length=1, max_length=40),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    interval: Interval = Query(default=Interval.RAW),
    session: AsyncSession = Depends(get_async_session),
) -> list[PricePointRead] | list[PriceBucketRead]:
    return await get_item_price_history(
        session=session,
        item_id=item_id,
        source=source,
        from_ts=from_ts,
        to_ts=to_ts,
        interval=interval.value,
    )
