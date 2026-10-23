from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_active_user
from app.auth.models import User
from app.core.db import get_async_session
from app.core.rate_limit import limiter
from app.imports import services
from app.imports.schemas import ImportFileResult
from app.market import services as market

router = APIRouter(tags=["import"])


@router.post("/import", response_model=list[ImportFileResult])
@limiter.limit("10/minute")
async def import_files(
    request: Request,
    files: list[UploadFile] = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ImportFileResult]:
    # Read before the loop: a failed file rolls the shared session back and expires `user`.
    user_id, is_superuser = user.id, user.is_superuser
    results = []
    for f in files:
        data = await f.read(market.MAX_FILE_BYTES + 1)
        results.append(
            await services.import_file(
                session, user_id, is_superuser, f.filename or "", data
            )
        )
    return results
