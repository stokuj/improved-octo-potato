from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import get_async_session
from app.config.rate_limit import limiter
from app.ingest.dependencies import verify_ingest_token
from app.ingest.schemas import IngestRequest, IngestResponse
from app.ingest.services import bulk_ingest

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/prices",
    response_model=IngestResponse,
    dependencies=[Depends(verify_ingest_token)],
)
@limiter.limit("60/minute")
async def ingest_prices(
    request: Request,
    payload: IngestRequest,
    session: AsyncSession = Depends(get_async_session),
) -> IngestResponse:
    return await bulk_ingest(session, payload)
