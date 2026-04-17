from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_user
from app.config.db import get_async_session
from app.items.models import ItemCategory, ItemGrade
from app.items.schemas import PaginatedItems
from app.user_items import services
from app.users.models import User

router = APIRouter(prefix="/user-items", tags=["user-items"])


@router.get("/me", response_model=PaginatedItems)
async def read_my_followed_items(
    q: str | None = Query(default=None),
    category: ItemCategory | None = Query(default=None),
    grade: ItemGrade | None = Query(default=None),
    offset: int = 0,
    limit: int = 20,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedItems:
    return await services.get_followed_items(
        session=session,
        user_id=user.id,
        q=q,
        category=category,
        grade=grade,
        offset=offset,
        limit=limit,
    )


@router.get("/ids", response_model=list[int])
async def read_my_followed_item_ids(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[int]:
    return await services.get_followed_item_ids(session=session, user_id=user.id)


@router.post("/{item_id}", status_code=status.HTTP_201_CREATED)
async def follow_item(
    item_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    newly_followed = await services.follow_item(
        session=session, user_id=user.id, item_id=item_id
    )
    if not newly_followed:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return Response(status_code=status.HTTP_201_CREATED)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_item(
    item_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    await services.unfollow_item(session=session, user_id=user.id, item_id=item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
