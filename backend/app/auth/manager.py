import uuid
from typing import Optional

from fastapi import Request
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from sqlmodel import select

from app.config.db import async_session_maker
from app.config.settings import settings
from app.profiles.models import Profile
from app.users.models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.reset_token_secret
    verification_token_secret = settings.verification_token_secret

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        async with async_session_maker() as session:
            result = await session.exec(
                select(Profile).where(Profile.user_id == user.id)
            )
            profile = result.one_or_none()
            if profile is None:
                session.add(Profile(user_id=user.id, is_private=True))
                await session.commit()

        print(f"User {user.id} has registered.")
