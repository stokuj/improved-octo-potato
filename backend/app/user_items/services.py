import uuid
from sqlmodel import and_, col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.exceptions import NotFoundError
from app.items.models import Item, ItemCategory, ItemGrade
from app.items.schemas import ItemListItem, PaginatedItems
from app.user_items.models import UserItem


async def get_followed_items(
    session: AsyncSession,
    user_id: uuid.UUID,
    q: str | None = None,
    category: ItemCategory | None = None,
    grade: ItemGrade | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PaginatedItems:
    statement = (
        select(UserItem, Item)
        .join(Item, Item.id == UserItem.item_id)
        .where(UserItem.user_id == user_id)
    )

    if q is not None:
        statement = statement.where(col(Item.name).contains(q))
    if category is not None:
        statement = statement.where(Item.category == category)
    if grade is not None:
        statement = statement.where(Item.grade == grade)

    count_statement = select(func.count()).select_from(statement.subquery())
    total_result = await session.exec(count_statement)
    total = total_result.one()

    rows_result = await session.exec(
        statement.order_by(UserItem.created_at.desc()).offset(offset).limit(limit)
    )
    rows = rows_result.all()

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


async def get_followed_item_ids(session: AsyncSession, user_id: uuid.UUID) -> list[int]:
    result = await session.exec(
        select(UserItem.item_id).where(UserItem.user_id == user_id)
    )
    return list(result.all())


async def follow_item(session: AsyncSession, user_id: uuid.UUID, item_id: int) -> bool:
    """Returns True if newly followed, False if already followed."""
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    result = await session.exec(
        select(UserItem).where(
            and_(UserItem.user_id == user_id, UserItem.item_id == item_id)
        )
    )
    existing = result.one_or_none()

    if existing is not None:
        return False

    user_item = UserItem(user_id=user_id, item_id=item_id)
    session.add(user_item)
    await session.commit()
    return True


async def unfollow_item(
    session: AsyncSession, user_id: uuid.UUID, item_id: int
) -> None:
    result = await session.exec(
        select(UserItem).where(
            and_(UserItem.user_id == user_id, UserItem.item_id == item_id)
        )
    )
    relation = result.one_or_none()

    if relation is not None:
        await session.delete(relation)
        await session.commit()
