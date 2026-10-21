# fastapi-users UserManager.
import uuid

from fastapi_users.manager import BaseUserManager, UUIDIDMixin

from app.core.settings import settings
from app.auth.models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.reset_token_secret
    verification_token_secret = settings.verification_token_secret
