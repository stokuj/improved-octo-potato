from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from sqladmin.authentication import AuthenticationBackend
from sqlmodel import select

from app.auth.dependencies import get_user_manager, get_user_db
from app.config.db import async_session_maker
from app.config.settings import settings
from app.users.models import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = str(form.get("username"))
        password = str(form.get("password"))

        async with async_session_maker() as session:
            async for user_db in get_user_db(session):
                async for user_manager in get_user_manager(user_db):
                    try:
                        user = await user_manager.authenticate(email, password)
                    except Exception:
                        return False

                    if user and user.is_superuser and user.is_active:
                        request.session.update({"user_id": str(user.id)})
                        return True
        return False

    async def logout(self, request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(location=request.url_for("admin:login"))

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False

        async with async_session_maker() as session:
            user = await session.get(User, user_id)
            if user and user.is_superuser and user.is_active:
                return True
        return False


authentication_backend = AdminAuth(secret_key=settings.admin_session_secret)


# Wrap login and authenticate to enforce secure session cookie if needed
# Note: starlette SessionMiddleware uses session cookie
class SecureAdminAuth(AdminAuth):
    def __init__(self, secret_key: str, secure: bool = False):
        super().__init__(secret_key)
        from starlette.middleware.sessions import SessionMiddleware
        from starlette.middleware import Middleware

        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                https_only=secure,
                same_site="lax",
            ),
        ]


authentication_backend = SecureAdminAuth(
    secret_key=settings.admin_session_secret, secure=settings.cookie_secure
)
