from collections import defaultdict

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.crafting.calculator import build_craft_tree
from app.crafting.models import Recipe, RecipeIngredient
from app.crafting.schemas import CraftResult, CraftSummary
from app.items.models import Item


async def load_all_recipes(
    session: AsyncSession,
) -> dict[int, tuple[Recipe, list[RecipeIngredient]]]:
    recipes = (await session.exec(select(Recipe))).all()
    ingredients = (await session.exec(select(RecipeIngredient))).all()
    ing_by_recipe: dict[int, list[RecipeIngredient]] = defaultdict(list)
    for ing in ingredients:
        ing_by_recipe[ing.recipe_id].append(ing)
    return {r.item_id: (r, ing_by_recipe[r.id]) for r in recipes}


async def load_all_items(session: AsyncSession) -> dict[int, Item]:
    items = (await session.exec(select(Item))).all()
    return {item.id: item for item in items}


async def calculate(
    session: AsyncSession,
    item_id: int,
    multiplier: int,
    inventory: dict[int, int],
) -> CraftResult:
    all_recipes = await load_all_recipes(session)
    all_items = await load_all_items(session)
    return build_craft_tree(item_id, multiplier, inventory, all_recipes, all_items)


async def list_summaries(session: AsyncSession) -> list[CraftSummary]:
    all_recipes = await load_all_recipes(session)
    all_items = await load_all_items(session)
    summaries = []
    for item_id in all_recipes:
        result = build_craft_tree(item_id, 1, {}, all_recipes, all_items)
        summaries.append(
            CraftSummary(
                item_id=result.item_id,
                item_name=result.item_name,
                output_qty=result.output_qty,
                total_material_cost=result.total_material_cost,
                market_price=result.market_price,
                batch_profit=result.batch_profit,
            )
        )
    return summaries
