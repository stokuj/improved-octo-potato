# backend/app/crafting/calculator.py
from math import ceil

from app.config.exceptions import AppError
from app.crafting.models import Recipe, RecipeIngredient
from app.crafting.schemas import CraftNode, CraftResult
from app.items.models import Item

RecipeMap = dict[int, tuple[Recipe, list[RecipeIngredient]]]
ItemMap = dict[int, Item]


def build_craft_tree(
    item_id: int,
    multiplier: int,
    inventory: dict[int, int],
    all_recipes: RecipeMap,
    all_items: ItemMap,
) -> CraftResult:
    if item_id not in all_recipes:
        raise AppError("Item has no recipe", status_code=404)

    recipe, ingredients = all_recipes[item_id]
    item = all_items[item_id]

    nodes: list[CraftNode] = []
    total_material_cost = 0
    has_missing_prices = False

    for ing in ingredients:
        qty_needed = ing.quantity * multiplier
        node = _build_node(
            item_id=ing.ingredient_item_id,
            qty_needed=qty_needed,
            inventory=inventory,
            all_recipes=all_recipes,
            all_items=all_items,
            visited={item_id},
            depth=1,
        )
        nodes.append(node)
        total_material_cost += node.total_cost
        if node.unit_price is None:
            has_missing_prices = True

    market_price = item.current_price
    profit = (
        market_price * recipe.output_qty * multiplier - total_material_cost
        if market_price is not None and not has_missing_prices
        else None
    )

    return CraftResult(
        item_id=item_id,
        item_name=item.name,
        output_qty=recipe.output_qty,
        multiplier=multiplier,
        market_price=market_price,
        batch_profit=profit,
        total_material_cost=total_material_cost,
        has_missing_prices=has_missing_prices,
        ingredients=nodes,
    )


def _build_node(
    item_id: int,
    qty_needed: int,
    inventory: dict[int, int],
    all_recipes: RecipeMap,
    all_items: ItemMap,
    visited: set[int],
    depth: int,
) -> CraftNode:
    if depth >= 10:
        name = all_items[item_id].name if item_id in all_items else str(item_id)
        raise AppError(f"Max depth exceeded at '{name}'", status_code=400)

    if item_id in visited:
        name = all_items[item_id].name if item_id in all_items else str(item_id)
        raise AppError(f"Cycle detected at '{name}'", status_code=400)

    item = all_items[item_id]
    unit_price = item.current_price
    total_cost = qty_needed * (unit_price or 0)
    can_craft = item_id in all_recipes

    crafts_possible: int | None = None
    if inventory:
        have = inventory.get(item_id, 0)
        crafts_possible = have // qty_needed if qty_needed > 0 else 0

    sub_ingredients: list[CraftNode] = []
    recipe_output_qty: int | None = None
    if can_craft:
        recipe, ingredients = all_recipes[item_id]
        recipe_output_qty = recipe.output_qty
        crafts_needed = ceil(qty_needed / recipe.output_qty)
        new_visited = visited | {item_id}
        for ing in ingredients:
            child_node = _build_node(
                item_id=ing.ingredient_item_id,
                qty_needed=ing.quantity * crafts_needed,
                inventory=inventory,
                all_recipes=all_recipes,
                all_items=all_items,
                visited=new_visited,
                depth=depth + 1,
            )
            sub_ingredients.append(child_node)

    return CraftNode(
        item_id=item_id,
        item_name=item.name,
        qty_needed=qty_needed,
        unit_price=unit_price,
        total_cost=total_cost,
        can_craft=can_craft,
        crafts_possible=crafts_possible,
        output_qty=recipe_output_qty,
        ingredients=sub_ingredients,
    )
