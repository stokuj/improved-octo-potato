from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item, ItemCategory, ItemGrade
from app.items.schemas import ItemListItem, ItemRead

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[ItemListItem])
def read_items(
    category: ItemCategory | None = Query(default=None),
    grade: ItemGrade | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ItemListItem]:
    statement = select(Item)
    if category is not None:
        statement = statement.where(Item.category == category)
    if grade is not None:
        statement = statement.where(Item.grade == grade)

    rows = session.exec(statement.order_by(Item.name)).all()
    return [
        ItemListItem(
            id=row.id,
            name=row.name,
            category=row.category,
            grade=row.grade,
            current_price=row.current_price,
        )
        for row in rows
    ]


@router.get("/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: Session = Depends(get_session)) -> Item:
    item = session.get(Item, item_id)
    if not item:
        raise NotFoundError()
    return ItemRead(
        id=item.id,
        name=item.name,
        category=item.category,
        grade=item.grade,
        current_price=item.current_price,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
