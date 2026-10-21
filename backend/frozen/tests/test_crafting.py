# backend/tests/test_crafting.py
import os
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.crafting.models import Recipe, RecipeIngredient
from app.items.models import Item, ItemCategory, ItemGrade

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture()
async def db_session():
    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def crafting_setup(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:6]
    sword = Item(
        name=f"Craft-Sword-{uid}",
        category=ItemCategory.WEAPONS,
        grade=ItemGrade.RARE,
        current_price=10000,
    )
    ingot = Item(
        name=f"Craft-Ingot-{uid}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.GRAND,
        current_price=1000,
    )
    ore = Item(
        name=f"Craft-Ore-{uid}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.GRAND,
        current_price=100,
    )
    db_session.add_all([sword, ingot, ore])
    await db_session.commit()
    for obj in [sword, ingot, ore]:
        await db_session.refresh(obj)

    sword_recipe = Recipe(item_id=sword.id, output_qty=1)
    db_session.add(sword_recipe)
    await db_session.commit()
    await db_session.refresh(sword_recipe)

    ingot_recipe = Recipe(item_id=ingot.id, output_qty=1)
    db_session.add(ingot_recipe)
    await db_session.commit()
    await db_session.refresh(ingot_recipe)

    db_session.add(
        RecipeIngredient(
            recipe_id=sword_recipe.id, ingredient_item_id=ingot.id, quantity=5
        )
    )
    db_session.add(
        RecipeIngredient(
            recipe_id=ingot_recipe.id, ingredient_item_id=ore.id, quantity=3
        )
    )
    await db_session.commit()

    return {"sword": sword, "ingot": ingot, "ore": ore}


async def test_calculate_basic(client: AsyncClient, crafting_setup):
    sword = crafting_setup["sword"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate", json={"multiplier": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == sword.id
    assert data["total_material_cost"] == 5000  # 5 ingots * 1000
    assert data["batch_profit"] == 5000  # 10000 - 5000
    assert len(data["ingredients"]) == 1
    ingot_node = data["ingredients"][0]
    assert ingot_node["qty_needed"] == 5
    assert ingot_node["can_craft"] is True
    assert len(ingot_node["ingredients"]) == 1  # nested: ore
    ore_node = ingot_node["ingredients"][0]
    assert ore_node["qty_needed"] == 15  # 5 ingots * 3 ore each
    assert ore_node["can_craft"] is False


async def test_calculate_with_multiplier(client: AsyncClient, crafting_setup):
    sword = crafting_setup["sword"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate", json={"multiplier": 3}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_material_cost"] == 15000
    assert data["ingredients"][0]["qty_needed"] == 15


async def test_calculate_with_inventory(client: AsyncClient, crafting_setup):
    sword = crafting_setup["sword"]
    ingot = crafting_setup["ingot"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate",
        json={"multiplier": 1, "inventory": {str(ingot.id): 22}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingredients"][0]["crafts_possible"] == 4  # floor(22/5)


async def test_calculate_no_recipe_returns_404(client: AsyncClient, crafting_setup):
    ore = crafting_setup["ore"]
    resp = await client.post(f"/api/crafting/{ore.id}/calculate", json={})
    assert resp.status_code == 404


async def test_calculate_unknown_item_returns_404(client: AsyncClient):
    resp = await client.post("/api/crafting/99999999/calculate", json={})
    assert resp.status_code == 404


async def test_list_summaries(client: AsyncClient, crafting_setup):
    resp = await client.get("/api/crafting/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    item_ids = [d["item_id"] for d in data]
    assert crafting_setup["sword"].id in item_ids
    assert crafting_setup["ingot"].id in item_ids
    sword_summary = next(d for d in data if d["item_id"] == crafting_setup["sword"].id)
    assert sword_summary["total_material_cost"] == 5000
    assert sword_summary["batch_profit"] == 5000


async def test_calculate_multiplier_too_large_returns_422(
    client: AsyncClient, crafting_setup
):
    sword = crafting_setup["sword"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate", json={"multiplier": 10_001}
    )
    assert resp.status_code == 422


async def test_calculate_multiplier_zero_returns_422(
    client: AsyncClient, crafting_setup
):
    sword = crafting_setup["sword"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate", json={"multiplier": 0}
    )
    assert resp.status_code == 422


async def test_calculate_negative_inventory_returns_422(
    client: AsyncClient, crafting_setup
):
    sword = crafting_setup["sword"]
    ingot = crafting_setup["ingot"]
    resp = await client.post(
        f"/api/crafting/{sword.id}/calculate",
        json={"multiplier": 1, "inventory": {str(ingot.id): -1}},
    )
    assert resp.status_code == 422


async def test_calculate_has_missing_prices_when_ingredient_has_no_price(
    client: AsyncClient, db_session: AsyncSession
):
    # Item with no price as ingredient → has_missing_prices=True, profit=null
    uid2 = uuid.uuid4().hex[:6]
    output = Item(
        name=f"MP-Output-{uid2}",
        category=ItemCategory.WEAPONS,
        grade=ItemGrade.RARE,
        current_price=5000,
    )
    ingredient = Item(
        name=f"MP-Ingr-{uid2}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.GRAND,
        current_price=None,
    )
    db_session.add_all([output, ingredient])
    await db_session.commit()
    for obj in [output, ingredient]:
        await db_session.refresh(obj)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=3
        )
    )
    await db_session.commit()

    resp = await client.post(
        f"/api/crafting/{output.id}/calculate", json={"multiplier": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_missing_prices"] is True
    assert data["batch_profit"] is None
    assert data["total_material_cost"] == 0  # ingredient treated as 0 cost
