from fastapi import APIRouter, Depends, Path, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_active_user
from app.auth.models import User
from app.core.db import get_async_session
from app.inventory import icons, services
from app.inventory.schemas import CharacterRead, ChestRead

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/characters", response_model=list[CharacterRead])
async def read_characters(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[CharacterRead]:
    return await services.list_characters(session, user.id)


@router.get("/chests", response_model=list[ChestRead])
async def read_chests(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ChestRead]:
    return await services.list_chests(session, user.id)


@router.get("/icons/{item_type}.png", response_class=Response)
async def read_icon(item_type: int = Path(ge=1)) -> Response:
    """Public: game art only, no user data. 404 lets the frontend show the grade colour."""
    try:
        data = await icons.get_icon(item_type)
    except icons.FetchBudgetExceeded:
        return Response(status_code=503)
    if data is None:
        return Response(status_code=404)
    return Response(
        data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800"},
    )
