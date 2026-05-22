from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import exceptions as fu_exc
from fastapi_users.router.common import ErrorCode
from pydantic import BaseModel, EmailStr

from app.auth.backend import auth_backend
from app.auth.dependencies import fastapi_users, get_user_manager
from app.auth.schemas import UserCreate, UserRead, UserUpdate
from app.config.rate_limit import limiter

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# --- Throttled endpoints (registered FIRST — FastAPI picks the first match) ---


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


@router.post(
    "/auth/register",
    tags=["auth"],
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def register_throttled(
    request: Request,
    user_create: UserCreate,
    user_manager=Depends(get_user_manager),
):
    try:
        created = await user_manager.create(user_create, safe=True, request=request)
    except fu_exc.UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
        )
    except fu_exc.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": ErrorCode.REGISTER_INVALID_PASSWORD, "reason": e.reason},
        )
    return UserRead.model_validate(created)


@router.post(
    "/auth/forgot-password", tags=["auth"], status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("5/hour")
async def forgot_throttled(
    request: Request,
    body: ForgotPasswordRequest,
    user_manager=Depends(get_user_manager),
):
    try:
        user = await user_manager.get_by_email(body.email)
        await user_manager.forgot_password(user, request)
    except (fu_exc.UserNotExists, fu_exc.UserInactive):
        # Silent — don't leak account existence
        return None
    return None


@router.post("/auth/reset-password", tags=["auth"])
@limiter.limit("5/hour")
async def reset_throttled(
    request: Request,
    body: ResetPasswordRequest,
    user_manager=Depends(get_user_manager),
):
    try:
        await user_manager.reset_password(body.token, body.password, request)
    except (
        fu_exc.InvalidResetPasswordToken,
        fu_exc.UserNotExists,
        fu_exc.UserInactive,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
        )
    except fu_exc.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )


# --- Then mount the rest of fastapi-users routers ---
# FastAPI matches the first registered route per (method, path), so the
# throttled endpoints above take precedence over the duplicates here.

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
