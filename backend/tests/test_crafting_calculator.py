# backend/tests/test_crafting_calculator.py
import pytest
from app.crafting.calculator import build_craft_tree
from app.crafting.models import Recipe, RecipeIngredient
from app.crafting.schemas import CraftResult
from app.config.exceptions import AppError
from app.items.models import Item, ItemCategory, ItemGrade


def _make_item(id: int, name: str, price: int | None = 1000) -> Item:
    return Item(
        id=id,
        name=name,
        category=ItemCategory.OTHER,
        grade=ItemGrade.GRAND,
        current_price=price,
    )


def _make_recipe(id: int, item_id: int, output_qty: int = 1) -> Recipe:
    return Recipe(id=id, item_id=item_id, output_qty=output_qty)


def _make_ing(
    id: int, recipe_id: int, ingredient_item_id: int, quantity: int
) -> RecipeIngredient:
    return RecipeIngredient(
        id=id,
        recipe_id=recipe_id,
        ingredient_item_id=ingredient_item_id,
        quantity=quantity,
    )


def test_basic_single_ingredient():
    # Sword (1000¤) needs 5 Ingots (200¤ each) → cost 1000, profit 0
    sword = _make_item(1, "Sword", price=1000)
    ingot = _make_item(2, "Ingot", price=200)
    recipe = _make_recipe(1, item_id=1, output_qty=1)
    ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=5)
    all_recipes = {1: (recipe, [ing])}
    all_items = {1: sword, 2: ingot}

    result = build_craft_tree(1, 1, {}, all_recipes, all_items)

    assert isinstance(result, CraftResult)
    assert result.item_id == 1
    assert result.total_material_cost == 1000  # 5 * 200
    assert result.profit_per_craft == 0  # 1000 - 1000
    assert len(result.ingredients) == 1
    assert result.ingredients[0].qty_needed == 5
    assert result.ingredients[0].total_cost == 1000
    assert result.ingredients[0].can_craft is False
    assert result.ingredients[0].crafts_possible is None


def test_multiplier_scales_quantities():
    sword = _make_item(1, "Sword", price=1000)
    ingot = _make_item(2, "Ingot", price=200)
    recipe = _make_recipe(1, item_id=1, output_qty=1)
    ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=5)
    all_recipes = {1: (recipe, [ing])}
    all_items = {1: sword, 2: ingot}

    result = build_craft_tree(1, 3, {}, all_recipes, all_items)

    assert result.ingredients[0].qty_needed == 15  # 5 * 3
    assert result.total_material_cost == 3000  # 15 * 200


def test_inventory_sets_crafts_possible():
    sword = _make_item(1, "Sword", price=1000)
    ingot = _make_item(2, "Ingot", price=200)
    recipe = _make_recipe(1, item_id=1, output_qty=1)
    ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=5)
    all_recipes = {1: (recipe, [ing])}
    all_items = {1: sword, 2: ingot}

    result = build_craft_tree(1, 1, {2: 22}, all_recipes, all_items)

    # have 22 ingots, need 5 → can do 4 crafts (floor(22/5))
    assert result.ingredients[0].crafts_possible == 4


def test_nested_recipe_expands():
    # Sword → 5 Ingots; Ingot → 3 Ore
    sword = _make_item(1, "Sword", price=10000)
    ingot = _make_item(2, "Ingot", price=1000)
    ore = _make_item(3, "Ore", price=100)

    sword_recipe = _make_recipe(1, item_id=1, output_qty=1)
    ingot_recipe = _make_recipe(2, item_id=2, output_qty=1)
    sword_ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=5)
    ingot_ing = _make_ing(2, recipe_id=2, ingredient_item_id=3, quantity=3)

    all_recipes = {1: (sword_recipe, [sword_ing]), 2: (ingot_recipe, [ingot_ing])}
    all_items = {1: sword, 2: ingot, 3: ore}

    result = build_craft_tree(1, 1, {}, all_recipes, all_items)

    ingot_node = result.ingredients[0]
    assert ingot_node.can_craft is True
    assert len(ingot_node.ingredients) == 1
    ore_node = ingot_node.ingredients[0]
    assert ore_node.qty_needed == 15  # 5 ingots * 3 ore each
    assert ore_node.can_craft is False


def test_output_qty_greater_than_one():
    # Recipe produces 5 ingots per craft; need 10 ingots → ceil(10/5)=2 crafts → 2*3=6 ore
    sword = _make_item(1, "Sword", price=5000)
    ingot = _make_item(2, "Ingot", price=1000)
    ore = _make_item(3, "Ore", price=100)

    sword_recipe = _make_recipe(1, item_id=1, output_qty=1)
    ingot_recipe = _make_recipe(2, item_id=2, output_qty=5)
    sword_ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=10)
    ingot_ing = _make_ing(2, recipe_id=2, ingredient_item_id=3, quantity=3)

    all_recipes = {1: (sword_recipe, [sword_ing]), 2: (ingot_recipe, [ingot_ing])}
    all_items = {1: sword, 2: ingot, 3: ore}

    result = build_craft_tree(1, 1, {}, all_recipes, all_items)
    ingot_node = result.ingredients[0]
    ore_node = ingot_node.ingredients[0]
    # Need 10 ingots; ingot recipe makes 5 → 2 crafts needed → 2 * 3 = 6 ore
    assert ore_node.qty_needed == 6


def test_cycle_detection_raises_400():
    # A → B → A
    item_a = _make_item(1, "A")
    item_b = _make_item(2, "B")
    recipe_a = _make_recipe(1, item_id=1)
    recipe_b = _make_recipe(2, item_id=2)
    ing_a = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=1)
    ing_b = _make_ing(2, recipe_id=2, ingredient_item_id=1, quantity=1)
    all_recipes = {1: (recipe_a, [ing_a]), 2: (recipe_b, [ing_b])}
    all_items = {1: item_a, 2: item_b}

    with pytest.raises(AppError) as exc_info:
        build_craft_tree(1, 1, {}, all_recipes, all_items)
    assert exc_info.value.status_code == 400
    assert "Cycle" in exc_info.value.detail


def test_depth_limit_raises_400():
    # Chain of 11 items: 1→2→3→...→11
    items = {i: _make_item(i, f"Item{i}") for i in range(1, 12)}
    recipes = {}
    for i in range(1, 11):
        recipe = _make_recipe(i, item_id=i)
        ing = _make_ing(i, recipe_id=i, ingredient_item_id=i + 1, quantity=1)
        recipes[i] = (recipe, [ing])

    with pytest.raises(AppError) as exc_info:
        build_craft_tree(1, 1, {}, recipes, items)
    assert exc_info.value.status_code == 400


def test_null_market_price_gives_null_profit():
    sword = _make_item(1, "Sword", price=None)
    ingot = _make_item(2, "Ingot", price=200)
    recipe = _make_recipe(1, item_id=1)
    ing = _make_ing(1, recipe_id=1, ingredient_item_id=2, quantity=5)
    all_recipes = {1: (recipe, [ing])}
    all_items = {1: sword, 2: ingot}

    result = build_craft_tree(1, 1, {}, all_recipes, all_items)

    assert result.market_price is None
    assert result.profit_per_craft is None
