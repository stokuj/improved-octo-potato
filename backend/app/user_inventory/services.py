import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import and_, col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.exceptions import AppError, NotFoundError
from app.crafting.calculator import build_craft_tree
from app.crafting.services import load_all_items, load_all_recipes
from app.items.models import Item
from app.user_inventory.models import UserInventory
from app.user_inventory.schemas import InventoryItem


async def get_inventory(
    session: AsyncSession, user_id: uuid.UUID
) -> list[InventoryItem]:
    result = await session.exec(
        select(UserInventory, Item)
        .join(Item, Item.id == UserInventory.item_id)
        .where(UserInventory.user_id == user_id)
        .order_by(Item.name)
    )
    return [
        InventoryItem(
            item_id=item.id,
            item_name=item.name,
            category=item.category,
            grade=item.grade,
            quantity=row.quantity,
        )
        for row, item in result.all()
    ]


async def upsert_inventory(
    session: AsyncSession, user_id: uuid.UUID, item_id: int, quantity: int
) -> None:
    """Set quantity for an item. Deletes the row if quantity == 0."""
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    if quantity == 0:
        await session.exec(
            delete(UserInventory).where(
                and_(UserInventory.user_id == user_id, UserInventory.item_id == item_id)
            )
        )
        await session.commit()
        return

    # Atomic upsert — avoids IntegrityError from concurrent PUTs for the same user+item
    stmt = (
        pg_insert(UserInventory)
        .values(user_id=user_id, item_id=item_id, quantity=quantity)
        .on_conflict_do_update(
            constraint="uq_user_inventory",
            set_={"quantity": quantity},
        )
    )
    await session.execute(stmt)
    await session.commit()


def _collect_item_ids(nodes: list) -> set[int]:
    """Recursively collect all item_ids from a CraftNode ingredient list."""
    ids: set[int] = set()
    for node in nodes:
        ids.add(node.item_id)
        if node.ingredients:
            ids |= _collect_item_ids(node.ingredients)
    return ids


async def get_inventory_for_recipe(
    session: AsyncSession, user_id: uuid.UUID, item_id: int
) -> dict[int, int]:
    """Return {item_id: quantity} for all ingredients in the recipe tree."""
    all_recipes = await load_all_recipes(session)
    if item_id not in all_recipes:
        return {}

    all_items = await load_all_items(session)
    try:
        tree = build_craft_tree(item_id, 1, {}, all_recipes, all_items)
    except AppError:
        return {}

    ingredient_ids = _collect_item_ids(tree.ingredients)
    if not ingredient_ids:
        return {}

    result = await session.exec(
        select(UserInventory).where(
            and_(
                UserInventory.user_id == user_id,
                col(UserInventory.item_id).in_(ingredient_ids),
            )
        )
    )
    return {row.item_id: row.quantity for row in result.all()}
