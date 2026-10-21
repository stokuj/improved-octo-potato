from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_superuser
from app.core.db import get_async_session
from app.core.rate_limit import limiter
from app.market import services
from app.market.schemas import (
    ImportFileResult,
    ListingRead,
    MarketDayRead,
    MarketItemRead,
    SummaryRow,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.post(
    "/import",
    response_model=list[ImportFileResult],
    dependencies=[Depends(current_superuser)],
)
@limiter.limit("10/minute")
async def import_files(
    request: Request,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> list[ImportFileResult]:
    results = []
    for f in files:
        data = await f.read(services.MAX_FILE_BYTES + 1)
        results.append(await services.import_csv(session, f.filename or "", data))
    return results


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


@router.get("/items/{item_id}/listings", response_model=list[ListingRead])
async def read_listings(
    item_id: int, session: AsyncSession = Depends(get_async_session)
) -> list[ListingRead]:
    return await services.get_latest_listings(session, item_id)


@router.get("/summary", response_model=list[SummaryRow])
async def read_summary(
    session: AsyncSession = Depends(get_async_session),
) -> list[SummaryRow]:
    return await services.get_summary(session)
