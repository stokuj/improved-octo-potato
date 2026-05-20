# backend/tests/test_inventory.py
import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.crafting.models import Recipe, RecipeIngredient
from app.items.models import Item, ItemCategory, ItemGrade

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


def _email() -> str:
    return f"inv-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def db_session() -> AsyncSession:
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    return client


@pytest.fixture()
async def item(db_session: AsyncSession) -> Item:
    i = Item(
        name=f"Inv-Item-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    db_session.add(i)
    await db_session.commit()
    await db_session.refresh(i)
    return i


# --- auth guard ---


async def test_get_inventory_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/inventory/")
    assert resp.status_code == 401


async def test_put_inventory_requires_auth(client: AsyncClient, item: Item) -> None:
    resp = await client.put(f"/api/inventory/{item.id}", json={"quantity": 10})
    assert resp.status_code == 401


async def test_for_recipe_requires_auth(client: AsyncClient, item: Item) -> None:
    resp = await client.get(f"/api/inventory/for-recipe/{item.id}")
    assert resp.status_code == 401


# --- GET /api/inventory/ ---


async def test_get_inventory_empty(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/inventory/")
    assert resp.status_code == 200
    assert resp.json() == []


# --- PUT /api/inventory/{item_id} ---


async def test_upsert_inventory_creates_entry(
    auth_client: AsyncClient, item: Item
) -> None:
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 100})
    assert resp.status_code == 204

    resp = await auth_client.get("/api/inventory/")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_id"] == item.id
    assert data[0]["quantity"] == 100


async def test_upsert_inventory_updates_quantity(
    auth_client: AsyncClient, item: Item
) -> None:
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 50})
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 200})

    resp = await auth_client.get("/api/inventory/")
    data = resp.json()
    # Exactly 1 row — upsert must update, not insert a duplicate
    assert len(data) == 1
    assert data[0]["quantity"] == 200


async def test_upsert_inventory_zero_removes_entry(
    auth_client: AsyncClient, item: Item
) -> None:
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 50})
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 0})

    resp = await auth_client.get("/api/inventory/")
    assert resp.json() == []


async def test_upsert_inventory_unknown_item_returns_404(
    auth_client: AsyncClient,
) -> None:
    resp = await auth_client.put("/api/inventory/999999", json={"quantity": 1})
    assert resp.status_code == 404


async def test_upsert_inventory_negative_quantity_rejected(
    auth_client: AsyncClient, item: Item
) -> None:
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": -1})
    assert resp.status_code == 422


async def test_upsert_zero_when_no_row_is_noop(
    auth_client: AsyncClient, item: Item
) -> None:
    """PUT quantity=0 on an item with no existing row must return 204 and not create a row."""
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 0})
    assert resp.status_code == 204

    resp = await auth_client.get("/api/inventory/")
    assert resp.json() == []


async def test_inventory_isolated_between_users(
    client: AsyncClient, item: Item
) -> None:
    """User A's inventory must not be visible to user B."""
    email_a = _email()
    await client.post(
        "/api/auth/register", json={"email": email_a, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email_a, "password": "password123"}
    )
    await client.put(f"/api/inventory/{item.id}", json={"quantity": 777})

    email_b = _email()
    await client.post(
        "/api/auth/register", json={"email": email_b, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email_b, "password": "password123"}
    )

    resp = await client.get("/api/inventory/")
    assert resp.status_code == 200
    assert resp.json() == []


# --- GET /api/inventory/for-recipe/{item_id} ---


async def test_for_recipe_no_recipe_returns_empty(
    auth_client: AsyncClient, item: Item
) -> None:
    resp = await auth_client.get(f"/api/inventory/for-recipe/{item.id}")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_unknown_item_returns_empty(auth_client: AsyncClient) -> None:
    """Item with no recipe → for-recipe returns {}."""
    resp = await auth_client.get("/api/inventory/for-recipe/999999")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_returns_matching_inventory(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    output = Item(
        name=f"Output-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    ingredient = Item(
        name=f"Ingr-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=5
        )
    )
    await db_session.commit()

    await auth_client.put(f"/api/inventory/{ingredient.id}", json={"quantity": 50})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert str(ingredient.id) in data
    assert data[str(ingredient.id)] == 50


async def test_for_recipe_no_inventory_returns_empty(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Recipe exists but user has no inventory for any ingredient → returns {}."""
    output = Item(
        name=f"Output3-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    ingredient = Item(
        name=f"Ingr3-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=3
        )
    )
    await db_session.commit()

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_excludes_items_not_in_tree(
    auth_client: AsyncClient, db_session: AsyncSession, item: Item
) -> None:
    """Inventory items outside the recipe tree must not appear in the response."""
    output = Item(
        name=f"Output2-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    ingredient = Item(
        name=f"Ingr2-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=1
        )
    )
    await db_session.commit()

    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 999})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    data = resp.json()
    assert str(item.id) not in data


async def test_for_recipe_nested_tree(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """for-recipe must collect ingredients at all depths, not just level 1."""
    output = Item(
        name=f"OutN-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    intermediate = Item(
        name=f"MidN-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    raw = Item(
        name=f"RawN-{uuid.uuid4().hex[:6]}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    for obj in (output, intermediate, raw):
        db_session.add(obj)
    await db_session.commit()
    for obj in (output, intermediate, raw):
        await db_session.refresh(obj)

    r1 = Recipe(item_id=output.id, output_qty=1)
    db_session.add(r1)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=r1.id, ingredient_item_id=intermediate.id, quantity=1
        )
    )

    r2 = Recipe(item_id=intermediate.id, output_qty=1)
    db_session.add(r2)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(recipe_id=r2.id, ingredient_item_id=raw.id, quantity=2)
    )
    await db_session.commit()

    await auth_client.put(f"/api/inventory/{raw.id}", json={"quantity": 10})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    data = resp.json()
    assert str(raw.id) in data
    assert data[str(raw.id)] == 10
