from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func, col

from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item, ItemCategory, ItemGrade
from app.items.schemas import ItemListItem, ItemRead, PaginatedItems


router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=PaginatedItems)
def read_items(
    q: str | None = Query(default=None),
    category: ItemCategory | None = Query(default=None),
    grade: ItemGrade | None = Query(default=None),
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> PaginatedItems:
    statement = select(Item)
    if q is not None:
        statement = statement.where(col(Item.name).contains(q))
    if category is not None:
        statement = statement.where(Item.category == category)
    if grade is not None:
        statement = statement.where(Item.grade == grade)

    # Get total count for infinite scroll
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Get paginated rows
    rows = session.exec(statement.order_by(Item.name).offset(offset).limit(limit)).all()

    items = [
        ItemListItem(
            id=row.id,
            name=row.name,
            category=row.category,
            grade=row.grade,
            current_price=row.current_price,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return PaginatedItems(items=items, total=total, offset=offset, limit=limit)


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
