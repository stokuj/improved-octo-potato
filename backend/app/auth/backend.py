# fastapi-users cookie/JWT backend.
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

from app.core.settings import settings

SESSION_SECONDS = 7 * 24 * 3600

cookie_transport = CookieTransport(
    cookie_max_age=SESSION_SECONDS,
    cookie_secure=settings.cookie_secure,
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.auth_secret, lifetime_seconds=SESSION_SECONDS)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
