from datetime import datetime, timezone
from typing import Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.profiles.models import Profile
from app.profiles.schemas import ProfileUpdate


async def get_or_create_profile(session: AsyncSession, user_id: Any) -> Profile:
    result = await session.exec(select(Profile).where(Profile.user_id == user_id))
    profile = result.one_or_none()
    if profile is not None:
        return profile

    profile = Profile(user_id=user_id, is_private=True)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def update_profile(
    session: AsyncSession, profile: Profile, profile_in: ProfileUpdate
) -> Profile:
    updates = profile_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
