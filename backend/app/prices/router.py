from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import get_async_session
from app.prices import services
from app.prices.schemas import PriceBucketRead, PricePointCreate, PricePointRead

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
    return await services.get_item_price_history(
        session=session,
        item_id=item_id,
        source=source,
        from_ts=from_ts,
        to_ts=to_ts,
        interval=interval.value,
    )


@router.post(
    "/{item_id}/prices",
    response_model=PricePointRead,
    status_code=201,
)
async def create_price_point(
    item_id: int,
    data: PricePointCreate,
    session: AsyncSession = Depends(get_async_session),
) -> PricePointRead:
    point = await services.add_price_point(session, item_id, data)
    return PricePointRead(
        item_id=point.item_id,
        source=point.source,
        price=point.price,
        captured_at=point.captured_at,
    )
