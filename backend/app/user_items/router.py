from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session, and_, col, func, select

from app.auth.dependencies import current_user
from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item, ItemCategory, ItemGrade
from app.items.schemas import ItemListItem, PaginatedItems
from app.user_items.models import UserItem
from app.users.models import User

router = APIRouter(prefix="/user-items", tags=["user-items"])


@router.get("/me", response_model=PaginatedItems)
def read_my_followed_items(
    q: str | None = Query(default=None),
    category: ItemCategory | None = Query(default=None),
    grade: ItemGrade | None = Query(default=None),
    offset: int = 0,
    limit: int = 20,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> PaginatedItems:
    statement = (
        select(UserItem, Item)
        .join(Item, Item.id == UserItem.item_id)
        .where(UserItem.user_id == user.id)
    )

    if q is not None:
        statement = statement.where(col(Item.name).contains(q))
    if category is not None:
        statement = statement.where(Item.category == category)
    if grade is not None:
        statement = statement.where(Item.grade == grade)

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    rows = session.exec(
        statement.order_by(UserItem.created_at.desc()).offset(offset).limit(limit)
    ).all()

    items = [
        ItemListItem(
            id=item.id,
            name=item.name,
            category=item.category,
            grade=item.grade,
            current_price=item.current_price,
            updated_at=item.updated_at,
        )
        for _, item in rows
    ]

    return PaginatedItems(items=items, total=total, offset=offset, limit=limit)


@router.get("/ids", response_model=list[int])
def read_my_followed_item_ids(
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[int]:
    rows = session.exec(
        select(UserItem.item_id).where(UserItem.user_id == user.id)
    ).all()
    return rows


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
