from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_user
from app.config.db import get_async_session
from app.profiles.models import Profile
from app.profiles.schemas import ProfileRead, ProfileUpdate
from app.users.models import User

router = APIRouter(prefix="/profiles", tags=["profiles"])


async def get_or_create_profile(session: AsyncSession, user: User) -> Profile:
    result = await session.exec(select(Profile).where(Profile.user_id == user.id))
    profile = result.one_or_none()
    if profile is not None:
        return profile

    profile = Profile(user_id=user.id, is_private=True)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileRead)
async def read_my_profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Profile:
    return await get_or_create_profile(session, user)


@router.patch("/me", response_model=ProfileRead)
async def update_my_profile(
    profile_in: ProfileUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Profile:
    profile = await get_or_create_profile(session, user)

    updates = profile_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
