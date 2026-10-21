from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_superuser
from app.core.db import get_async_session
from app.core.rate_limit import limiter
from app.market import services
from app.market.schemas import ImportFileResult

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
