# fastapi-users UserManager.
import uuid

from fastapi import HTTPException, Request, status
from fastapi_users import exceptions
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from fastapi_users.router.common import ErrorCode

from app.core.settings import settings
from app.auth.models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.reset_token_secret
    verification_token_secret = settings.verification_token_secret

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        """Sign in an existing active superuser by email. Never creates users or
        stores OAuth accounts: accounts come only from the create-superuser CLI."""
        try:
            user = await self.get_by_email(account_email)
        except exceptions.UserNotExists:
            user = None
        if user is None or not user.is_active or not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )
        return user
