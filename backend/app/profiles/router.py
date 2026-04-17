from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_user
from app.config.db import get_async_session
from app.profiles.models import Profile
from app.profiles.schemas import ProfileRead, ProfileUpdate
from app.profiles.services import get_or_create_profile, update_profile
from app.users.models import User

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileRead)
async def read_my_profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Profile:
    return await get_or_create_profile(session, user.id)


@router.patch("/me", response_model=ProfileRead)
async def update_my_profile(
    profile_in: ProfileUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Profile:
    profile = await get_or_create_profile(session, user.id)
    return await update_profile(session, profile, profile_in)
