import uuid
from typing import Optional

from fastapi import Request
from fastapi_users.manager import BaseUserManager, UUIDIDMixin

from app.config.settings import settings
from app.users.models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        print(f"User {user.id} has registered.")
