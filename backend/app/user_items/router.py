from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session, and_, select

from app.auth.dependencies import current_user
from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item
from app.user_items.models import UserItem
from app.user_items.schemas import UserItemRead
from app.users.models import User

router = APIRouter(prefix="/user-items", tags=["user-items"])


@router.get("/me", response_model=list[UserItemRead])
def read_my_followed_items(
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[UserItemRead]:
    query = (
        select(UserItem, Item)
        .join(Item, Item.id == UserItem.item_id)
        .where(UserItem.user_id == user.id)
        .order_by(UserItem.created_at.desc())
    )
    rows = session.exec(query).all()
    return [
        UserItemRead(
            item_id=item.id,
            name=item.name,
            category=item.category,
            grade=item.grade,
            current_price=item.current_price,
            followed_at=user_item.created_at,
        )
        for user_item, item in rows
    ]


@router.post("/{item_id}", status_code=status.HTTP_201_CREATED)
def follow_item(
    item_id: int,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> Response:
    if session.get(Item, item_id) is None:
        raise NotFoundError("Item not found")

    existing = session.exec(
        select(UserItem).where(
            and_(UserItem.user_id == user.id, UserItem.item_id == item_id)
        )
    ).one_or_none()

    if existing is not None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    user_item = UserItem(user_id=user.id, item_id=item_id)
    session.add(user_item)
    session.commit()
    return Response(status_code=status.HTTP_201_CREATED)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_item(
    item_id: int,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> Response:
    relation = session.exec(
        select(UserItem).where(
            and_(UserItem.user_id == user.id, UserItem.item_id == item_id)
        )
    ).one_or_none()

    if relation is not None:
        session.delete(relation)
        session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
