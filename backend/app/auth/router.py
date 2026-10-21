from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.router.common import ErrorCode

from app.auth.backend import auth_backend
from app.auth.dependencies import fastapi_users, get_user_manager
from app.auth.schemas import UserRead, UserUpdate
from app.core.rate_limit import limiter

router = APIRouter()


# Throttled login is registered FIRST — FastAPI picks the first match, so it
# shadows the fastapi-users login route mounted below.
@router.post("/auth/login", tags=["auth"])
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


# Single-user app: no register / forgot / reset / verify routes.
# Accounts are created with `python -m app.auth.cli create-superuser`.
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
