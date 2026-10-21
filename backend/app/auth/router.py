from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.router.common import ErrorCode

from app.auth.backend import auth_backend
from app.auth.dependencies import fastapi_users, get_user_manager
from app.auth.oauth import google_client
from app.auth.schemas import UserRead, UserUpdate
from app.core.rate_limit import limiter
from app.core.settings import settings


@limiter.limit("5/minute")
async def login_throttled(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )
    return await auth_backend.login(strategy, user)


async def logout(
    user_token=Depends(fastapi_users.authenticator.current_user_token(active=True)),
    strategy=Depends(auth_backend.get_strategy),
):
    user, token = user_token
    return await auth_backend.logout(strategy, user, token)


def build_router(*, password_login: bool) -> APIRouter:
    """Auth routes. Single-user app: no register / forgot / reset / verify routes;
    accounts are created with `python -m app.auth.cli create-superuser`."""
    router = APIRouter()
    # Production signs in with Google only; dev and e2e keep the password form.
    if password_login:
        router.add_api_route(
            "/auth/login", login_throttled, methods=["POST"], tags=["auth"]
        )
    router.add_api_route(
        "/auth/logout", logout, methods=["POST"], status_code=204, tags=["auth"]
    )
    router.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )
    if google_client is not None:
        router.include_router(
            fastapi_users.get_oauth_router(
                google_client,
                auth_backend,
                settings.auth_secret,
                redirect_url=f"{settings.frontend_url}/auth/callback",
                csrf_token_cookie_secure=settings.cookie_secure,
            ),
            prefix="/auth/google",
            tags=["auth"],
        )
    return router


router = build_router(password_login=settings.environment != "prod")
