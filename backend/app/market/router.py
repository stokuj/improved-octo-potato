from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_async_session
from app.market import services
from app.market.schemas import ListingsRead, MarketDayRead, MarketItemRead

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/items", response_model=list[MarketItemRead])
async def read_items(
    session: AsyncSession = Depends(get_async_session),
) -> list[MarketItemRead]:
    return await services.list_items(session)


@router.get("/items/{item_id}/days", response_model=list[MarketDayRead])
async def read_days(
    item_id: int,
    days: int = Query(default=14, ge=1, le=60),
    session: AsyncSession = Depends(get_async_session),
) -> list[MarketDayRead]:
    return await services.get_days(session, item_id, days)


@router.get("/items/{item_id}/listings", response_model=ListingsRead)
async def read_listings(
    item_id: int, session: AsyncSession = Depends(get_async_session)
) -> ListingsRead:
    return await services.get_latest_listings(session, item_id)
