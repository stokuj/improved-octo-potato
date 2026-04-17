from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.exceptions import NotFoundError
from app.items.models import Item, ItemCategory, ItemGrade
from app.items.schemas import ItemListItem, PaginatedItems


async def get_items(
    session: AsyncSession,
    q: str | None = None,
    category: ItemCategory | None = None,
    grade: ItemGrade | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PaginatedItems:
    statement = select(Item)
    if q is not None:
        statement = statement.where(col(Item.name).contains(q))
    if category is not None:
        statement = statement.where(Item.category == category)
    if grade is not None:
        statement = statement.where(Item.grade == grade)

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total_result = await session.exec(count_statement)
    total = total_result.one()

    # Get paginated rows
    rows_result = await session.exec(
        statement.order_by(Item.name).offset(offset).limit(limit)
    )
    rows = rows_result.all()

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


async def get_item(session: AsyncSession, item_id: int) -> Item:
    item = await session.get(Item, item_id)
    if not item:
        raise NotFoundError()
    return item
