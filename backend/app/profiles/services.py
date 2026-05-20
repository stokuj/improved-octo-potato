import uuid
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.profiles.models import Profile, utcnow
from app.profiles.schemas import ProfileUpdate


async def get_or_create_profile(session: AsyncSession, user_id: uuid.UUID) -> Profile:
    stmt = (
        pg_insert(Profile)
        .values(user_id=user_id, is_private=True)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    result = await session.exec(stmt)  # type: ignore[arg-type]
    if result.rowcount:
        await session.commit()

    row = await session.exec(select(Profile).where(Profile.user_id == user_id))
    return row.one()


async def update_profile(
    session: AsyncSession, profile: Profile, profile_in: ProfileUpdate
) -> Profile:
    updates = profile_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    profile.updated_at = utcnow()
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
