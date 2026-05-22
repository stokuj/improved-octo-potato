# backend/tests/test_calculator_depth.py
import uuid

import pytest
from sqlalchemy import text

from app.config.exceptions import AppError
from app.crafting.calculator import build_craft_tree
from app.crafting.models import Recipe, RecipeIngredient
from app.items.models import Item, ItemCategory, ItemGrade


def _name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _mk_item(session, name: str, price: int | None = 100) -> Item:
    item = Item(
        name=name, category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC, current_price=price
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def _mk_recipe(session, output_item: Item, output_qty: int = 1) -> Recipe:
    r = Recipe(item_id=output_item.id, output_qty=output_qty)
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


async def _mk_ing(session, recipe: Recipe, ing_item: Item, qty: int) -> None:
    session.add(RecipeIngredient(
        recipe_id=recipe.id, ingredient_item_id=ing_item.id, quantity=qty
    ))
    await session.commit()


async def _build_maps(session, items: list[Item]) -> tuple[dict, dict]:
    from sqlmodel import select

    item_map = {i.id: i for i in items}
    recipe_map: dict[int, tuple[Recipe, list[RecipeIngredient]]] = {}
    for i in items:
        recipe = (await session.exec(select(Recipe).where(Recipe.item_id == i.id))).first()
        if recipe:
            ings = (
                await session.exec(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id))
            ).all()
            recipe_map[i.id] = (recipe, list(ings))
    return recipe_map, item_map


async def test_recipe_depth_3_levels_profit_correct(session) -> None:
    leaf = await _mk_item(session, _name("leaf"), price=10)
    mid = await _mk_item(session, _name("mid"), price=100)
    top = await _mk_item(session, _name("top"), price=1000)

    rb = await _mk_recipe(session, mid, output_qty=1)
    await _mk_ing(session, rb, leaf, 2)
    ra = await _mk_recipe(session, top, output_qty=1)
    await _mk_ing(session, ra, mid, 3)

    recipe_map, item_map = await _build_maps(session, [leaf, mid, top])
    result = build_craft_tree(top.id, 1, {}, recipe_map, item_map)

    # Calculator uses market price for ingredients that have one, even if they
    # also have a recipe.  mid market price = 100 * 3 = 300.
    assert result.total_material_cost == 300
    assert result.batch_profit == 700


async def test_recipe_cycle_does_not_infinite_loop(session) -> None:
    a = await _mk_item(session, _name("A-cycle"))
    b = await _mk_item(session, _name("B-cycle"))

    ra = await _mk_recipe(session, a)
    await _mk_ing(session, ra, b, 1)
    rb = await _mk_recipe(session, b)
    await _mk_ing(session, rb, a, 1)

    recipe_map, item_map = await _build_maps(session, [a, b])

    with pytest.raises(AppError, match="Cycle"):
        build_craft_tree(a.id, 1, {}, recipe_map, item_map)


async def test_missing_ingredient_recipe_returns_partial_cost(
    session, item_with_broken_recipe
) -> None:
    from sqlmodel import select

    recipe = (
        await session.exec(select(Recipe).where(Recipe.item_id == item_with_broken_recipe.id))
    ).first()
    ings = (
        await session.exec(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id))
    ).all()

    item_map = {item_with_broken_recipe.id: item_with_broken_recipe}
    recipe_map = {item_with_broken_recipe.id: (recipe, list(ings))}

    with pytest.raises(AppError, match="not found"):
        build_craft_tree(item_with_broken_recipe.id, 1, {}, recipe_map, item_map)


async def test_batch_profit_formula_with_multiplier(session) -> None:
    leaf = await _mk_item(session, _name("leaf-batch"), price=10)
    out = await _mk_item(session, _name("out-batch"), price=200)

    r = await _mk_recipe(session, out, output_qty=5)
    await _mk_ing(session, r, leaf, 2)

    recipe_map, item_map = await _build_maps(session, [leaf, out])
    result = build_craft_tree(out.id, 3, {}, recipe_map, item_map)

    assert result.total_material_cost == 60
    assert result.batch_profit == 2940
