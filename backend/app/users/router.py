from fastapi import APIRouter, Depends

from app.auth.dependencies import current_user
from app.auth.schemas import UserRead
from app.users.models import User

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(current_user)) -> User:
    return user
