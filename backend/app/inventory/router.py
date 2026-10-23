from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_active_user
from app.auth.models import User
from app.core.db import get_async_session
from app.inventory import services
from app.inventory.schemas import BagRead, CharacterRead

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/characters", response_model=list[CharacterRead])
async def read_characters(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[CharacterRead]:
    return await services.list_characters(session, user.id)


@router.get("/characters/{character}", response_model=BagRead)
async def read_bag(
    character: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> BagRead:
    return await services.get_bag(session, user.id, character)
