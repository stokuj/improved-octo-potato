# sqladmin auth: reuses the app's fastapiusersauth cookie (superusers only).
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from sqladmin.authentication import AuthenticationBackend

from app.auth.backend import cookie_transport, get_jwt_strategy
from app.auth.dependencies import get_user_manager, get_user_db
from app.core.db import async_session_maker
from app.core.settings import settings


def sign_in_redirect() -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url}/auth", status_code=302)


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        # Signing in happens on the frontend (/auth); the sqladmin form is not a way in.
        return False

    async def logout(self, request: Request) -> Response:
        request.session.clear()
        response = sign_in_redirect()
        # Same attributes fastapi-users sets the cookie with, so browsers drop that one.
        response.delete_cookie(
            cookie_transport.cookie_name,
            path=cookie_transport.cookie_path,
            domain=cookie_transport.cookie_domain,
            secure=cookie_transport.cookie_secure,
            httponly=cookie_transport.cookie_httponly,
            samesite=cookie_transport.cookie_samesite,
        )
        return response

    async def authenticate(self, request: Request) -> Response | bool:
        token = request.cookies.get(cookie_transport.cookie_name)
        if not token:
            return sign_in_redirect()

        async with async_session_maker() as session:
            async for user_db in get_user_db(session):
                async for user_manager in get_user_manager(user_db):
                    user = await get_jwt_strategy().read_token(token, user_manager)
                    if user and user.is_superuser and user.is_active:
                        return True
        return sign_in_redirect()


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
