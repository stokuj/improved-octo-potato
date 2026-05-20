# User Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-user item quantity storage in DB, a `/inventory` management page, and pre-fill "Have" in the recipe tree for logged-in users.

**Architecture:** New `app/user_inventory/` backend module (model, schemas, services, router) following the exact `user_items` pattern. Three API endpoints: list, upsert, and recipe-scoped fetch. Frontend: new `/inventory` route + navbar link + replace localStorage in item detail with API calls.

**Tech Stack:** FastAPI + SQLModel + PostgreSQL (Alembic migration), SvelteKit 5, DaisyUI.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/user_inventory/models.py` | `UserInventory` SQLModel table |
| Create | `backend/app/user_inventory/__init__.py` | empty package marker |
| Create | `backend/app/user_inventory/schemas.py` | Request/response Pydantic models |
| Create | `backend/app/user_inventory/services.py` | DB logic: get, upsert, delete, recipe-scoped |
| Create | `backend/app/user_inventory/router.py` | FastAPI routes |
| Modify | `backend/app/main.py` | Register inventory router |
| Modify | `backend/alembic/env.py` | Import UserInventory for autogenerate |
| Create | `backend/alembic/versions/<rev>_add_user_inventory.py` | Migration |
| Create | `backend/tests/test_inventory.py` | API tests (written first — TDD) |
| Create | `frontend/src/routes/inventory/+page.svelte` | Inventory management page |
| Modify | `frontend/src/routes/+layout.svelte` | Add "Inventory" nav link (auth-gated) |
| Modify | `frontend/src/routes/items/[id]/+page.svelte` | Replace localStorage with API calls |

---

## Task 1: Backend model + migration

**Files:**
- Create: `backend/app/user_inventory/models.py`
- Create: `backend/app/user_inventory/__init__.py`
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/<rev>_add_user_inventory.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/user_inventory/__init__.py
# (empty)
```

```python
# backend/app/user_inventory/models.py
import uuid

from sqlmodel import Field, SQLModel, UniqueConstraint


class UserInventory(SQLModel, table=True):
    __tablename__ = "userinventory"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_inventory"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    item_id: int = Field(foreign_key="item.id", index=True)
    quantity: int = Field(ge=0)
```

- [ ] **Step 2: Import in alembic/env.py**

Open `backend/alembic/env.py` and add after the last model import:
```python
from app.user_inventory.models import UserInventory  # noqa: F401
```

- [ ] **Step 3: Also import in conftest.py**

Open `backend/tests/conftest.py` and add after the existing model imports:
```python
from app.user_inventory.models import UserInventory  # noqa: F401
```

This ensures `setup_database` creates the `userinventory` table when the test DB schema is built.

- [ ] **Step 4: Generate migration**

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend
uv run alembic revision --autogenerate -m "add_user_inventory"
```

Expected output: `Generating .../versions/xxxx_add_user_inventory.py`

- [ ] **Step 5: Verify migration content**

Open the generated file and confirm it contains `op.create_table('userinventory', ...)` with columns `id`, `user_id`, `item_id`, `quantity` and the unique constraint.

- [ ] **Step 6: Apply migration**

```bash
uv run alembic upgrade head
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add backend/app/user_inventory/ backend/alembic/env.py backend/alembic/versions/ backend/tests/conftest.py
git commit -m "feat(backend): UserInventory model and migration"
```

---

## Task 2: Write failing tests (TDD — tests first)

**Files:**
- Create: `backend/tests/test_inventory.py`

Write the complete test suite *before* implementing the router. Running these tests should fail with `404` (routes not registered) or `ImportError`.

- [ ] **Step 1: Write test_inventory.py**

```python
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
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email, "password": "password123"})
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

async def test_upsert_inventory_creates_entry(auth_client: AsyncClient, item: Item) -> None:
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 100})
    assert resp.status_code == 204

    resp = await auth_client.get("/api/inventory/")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_id"] == item.id
    assert data[0]["quantity"] == 100


async def test_upsert_inventory_updates_quantity(auth_client: AsyncClient, item: Item) -> None:
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 50})
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 200})

    resp = await auth_client.get("/api/inventory/")
    data = resp.json()
    # Exactly 1 row — upsert must update, not insert a duplicate
    assert len(data) == 1
    assert data[0]["quantity"] == 200


async def test_upsert_inventory_zero_removes_entry(auth_client: AsyncClient, item: Item) -> None:
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 50})
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 0})

    resp = await auth_client.get("/api/inventory/")
    assert resp.json() == []


async def test_upsert_inventory_unknown_item_returns_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.put("/api/inventory/999999", json={"quantity": 1})
    assert resp.status_code == 404


async def test_upsert_inventory_negative_quantity_rejected(auth_client: AsyncClient, item: Item) -> None:
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": -1})
    assert resp.status_code == 422


# --- GET /api/inventory/for-recipe/{item_id} ---

async def test_for_recipe_no_recipe_returns_empty(auth_client: AsyncClient, item: Item) -> None:
    resp = await auth_client.get(f"/api/inventory/for-recipe/{item.id}")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_returns_matching_inventory(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    output = Item(name=f"Output-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    ingredient = Item(name=f"Ingr-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=5))
    await db_session.commit()

    await auth_client.put(f"/api/inventory/{ingredient.id}", json={"quantity": 50})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    assert resp.status_code == 200
    data = resp.json()
    # JSON object keys are always strings
    assert str(ingredient.id) in data
    assert data[str(ingredient.id)] == 50


async def test_for_recipe_excludes_items_not_in_tree(
    auth_client: AsyncClient, db_session: AsyncSession, item: Item
) -> None:
    """Inventory items outside the recipe tree must not appear in the response."""
    output = Item(name=f"Output2-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    ingredient = Item(name=f"Ingr2-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=1))
    await db_session.commit()

    # Set inventory for a completely unrelated item
    await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 999})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    data = resp.json()
    assert str(item.id) not in data


async def test_upsert_zero_when_no_row_is_noop(auth_client: AsyncClient, item: Item) -> None:
    """PUT quantity=0 on an item with no existing row must return 204 and not create a row."""
    resp = await auth_client.put(f"/api/inventory/{item.id}", json={"quantity": 0})
    assert resp.status_code == 204

    resp = await auth_client.get("/api/inventory/")
    assert resp.json() == []


async def test_inventory_isolated_between_users(client: AsyncClient, item: Item) -> None:
    """User A's inventory must not be visible to user B."""
    # Register and log in as user A
    email_a = _email()
    await client.post("/api/auth/register", json={"email": email_a, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email_a, "password": "password123"})
    await client.put(f"/api/inventory/{item.id}", json={"quantity": 777})

    # Log out and register as user B (reuse same client — cookies replaced on login)
    email_b = _email()
    await client.post("/api/auth/register", json={"email": email_b, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email_b, "password": "password123"})

    resp = await client.get("/api/inventory/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_for_recipe_unknown_item_returns_empty(auth_client: AsyncClient) -> None:
    """Item with no recipe → for-recipe returns {}."""
    resp = await auth_client.get("/api/inventory/for-recipe/999999")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_no_inventory_returns_empty(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Recipe exists but user has no inventory for any ingredient → returns {}."""
    output = Item(name=f"Output3-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    ingredient = Item(name=f"Ingr3-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    db_session.add(output)
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(output)
    await db_session.refresh(ingredient)

    recipe = Recipe(item_id=output.id, output_qty=1)
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_item_id=ingredient.id, quantity=3))
    await db_session.commit()

    # No PUT to inventory — user has nothing
    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    assert resp.status_code == 200
    assert resp.json() == {}


async def test_for_recipe_nested_tree(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """for-recipe must collect ingredients at all depths, not just level 1."""
    # output → intermediate → raw
    output = Item(name=f"OutN-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    intermediate = Item(name=f"MidN-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    raw = Item(name=f"RawN-{uuid.uuid4().hex[:6]}", category=ItemCategory.CRAFTING, grade=ItemGrade.BASIC)
    for obj in (output, intermediate, raw):
        db_session.add(obj)
    await db_session.commit()
    for obj in (output, intermediate, raw):
        await db_session.refresh(obj)

    # Recipe: output needs 1× intermediate
    r1 = Recipe(item_id=output.id, output_qty=1)
    db_session.add(r1)
    await db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=r1.id, ingredient_item_id=intermediate.id, quantity=1))

    # Recipe: intermediate needs 2× raw
    r2 = Recipe(item_id=intermediate.id, output_qty=1)
    db_session.add(r2)
    await db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=r2.id, ingredient_item_id=raw.id, quantity=2))
    await db_session.commit()

    await auth_client.put(f"/api/inventory/{raw.id}", json={"quantity": 10})

    resp = await auth_client.get(f"/api/inventory/for-recipe/{output.id}")
    data = resp.json()
    # raw is 2 levels deep — must still appear
    assert str(raw.id) in data
    assert data[str(raw.id)] == 10
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /home/dv6/GitHub/improved-octo-potato && make test 2>&1 | grep -E "FAILED|ERROR|passed|failed" | tail -10
```

Expected: all `test_inventory` tests fail — route doesn't exist yet, so every request returns 404.
- Auth tests (`expects 401`) fail as `AssertionError: assert 404 == 401` — correct, route must exist before auth can kick in.
- Functional tests (`expects 200/204`) fail as `AssertionError: assert 404 == 200` — correct.
The rest of the suite (non-inventory tests) should still pass.

- [ ] **Step 3: Commit failing tests**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add backend/tests/test_inventory.py
git commit -m "test(backend): failing inventory tests (TDD — red)"
```

---

## Task 3: Implement schemas, services, router (make tests green)

**Files:**
- Create: `backend/app/user_inventory/schemas.py`
- Create: `backend/app/user_inventory/services.py`
- Create: `backend/app/user_inventory/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/user_inventory/schemas.py
from pydantic import BaseModel, Field

from app.items.models import ItemCategory, ItemGrade


class InventoryUpsert(BaseModel):
    quantity: int = Field(ge=0)


class InventoryItem(BaseModel):
    item_id: int
    item_name: str
    category: ItemCategory
    grade: ItemGrade
    quantity: int
```

- [ ] **Step 2: Create services**

```python
# backend/app/user_inventory/services.py
import uuid

from sqlmodel import and_, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.exceptions import NotFoundError
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

    result = await session.exec(
        select(UserInventory).where(
            and_(UserInventory.user_id == user_id, UserInventory.item_id == item_id)
        )
    )
    existing = result.one_or_none()

    if quantity == 0:
        if existing is not None:
            await session.delete(existing)
            await session.commit()
        return

    if existing is None:
        session.add(UserInventory(user_id=user_id, item_id=item_id, quantity=quantity))
    else:
        existing.quantity = quantity

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
    except (RecursionError, ValueError):
        # Malformed recipe (cycle or depth guard) — treat as no tree
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
```

- [ ] **Step 3: Create router**

```python
# backend/app/user_inventory/router.py
from fastapi import APIRouter, Depends, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_user
from app.config.db import get_async_session
from app.user_inventory import services
from app.user_inventory.schemas import InventoryItem, InventoryUpsert
from app.users.models import User

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryItem])
async def read_inventory(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[InventoryItem]:
    return await services.get_inventory(session=session, user_id=user.id)


@router.get("/for-recipe/{item_id}", response_model=dict[int, int])
async def get_inventory_for_recipe(
    item_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[int, int]:
    return await services.get_inventory_for_recipe(
        session=session, user_id=user.id, item_id=item_id
    )


@router.put("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_inventory(
    item_id: int,
    body: InventoryUpsert,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    await services.upsert_inventory(
        session=session, user_id=user.id, item_id=item_id, quantity=body.quantity
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

**Note:** `GET /for-recipe/{item_id}` is registered before `PUT /{item_id}` to avoid any ambiguity with FastAPI route matching.

- [ ] **Step 4: Register router in main.py**

In `backend/app/main.py`, add after the other `user_*` imports:
```python
from app.user_inventory.router import router as inventory_router
```

And after `api.include_router(user_items_router)` (or the last `api.include_router` call):
```python
api.include_router(inventory_router)
```

- [ ] **Step 5: Run tests — confirm green**

```bash
cd /home/dv6/GitHub/improved-octo-potato && make test 2>&1 | grep -E "FAILED|ERROR|passed|failed" | tail -10
```

Expected: all `test_inventory` tests pass. Full suite passes.

- [ ] **Step 6: Ruff check**

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend
uv run ruff check app/user_inventory/ app/main.py
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add backend/app/user_inventory/ backend/app/main.py
git commit -m "feat(backend): inventory API — list, upsert, for-recipe endpoints (TDD green)"
```

---

## Task 4: Frontend — `/inventory` page + navbar link

**Files:**
- Create: `frontend/src/routes/inventory/+page.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Create inventory page**

```svelte
<!-- frontend/src/routes/inventory/+page.svelte -->
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { API_BASE_URL } from '$lib/config.js';
    import { user } from '$lib/auth.svelte.js';
    import { gradeColor } from '$lib/grades.js';

    /** @typedef {{ id: number, name: string, category: string, grade: string }} ItemRow */
    /** @typedef {{ item_id: number, item_name: string, category: string, grade: string, quantity: number }} InventoryRow */

    const CATEGORIES = [
        'Special Product','Weapons','Armor','Accessories','Instrument',
        'Costume','Consumables','Crafting','Machining','Companions',
        'Other','Lunagem','Lunastone'
    ];
    const GRADES = [
        'Basic','Grand','Rare','Arcane','Heroic','Unique',
        'Celestial','Divine','Epic','Legendary','Mythic','Eternal'
    ];

    /** @type {ItemRow[]} */
    let allItems = $state([]);
    /** @type {Record<number, number>} */
    let quantities = $state({});
    let loading = $state(true);
    let searchQuery = $state('');
    let selectedCategory = $state('');
    let selectedGrade = $state('');

    /** @type {Record<number, ReturnType<typeof setTimeout>>} */
    let debounceTimers = {};

    const filtered = $derived.by(() => {
        return allItems.filter(item => {
            if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
            if (selectedCategory && item.category !== selectedCategory) return false;
            if (selectedGrade && item.grade !== selectedGrade) return false;
            return true;
        });
    });

    async function loadData() {
        loading = true;
        try {
            const [itemsResp, invResp] = await Promise.all([
                fetch(`${API_BASE_URL}/items/?limit=1000`, { credentials: 'include' }),
                fetch(`${API_BASE_URL}/inventory/`, { credentials: 'include' }),
            ]);
            if (!itemsResp.ok) return;
            if (invResp.status === 401) { goto('/auth'); return; }
            if (!invResp.ok) return;

            const itemsData = await itemsResp.json();
            /** @type {InventoryRow[]} */
            const inv = await invResp.json();

            allItems = itemsData.items ?? [];
            quantities = Object.fromEntries(inv.map((/** @type {InventoryRow} */ r) => [r.item_id, r.quantity]));
        } finally {
            loading = false;
        }
    }

    /** @param {number} itemId @param {number} value */
    function handleQuantityChange(itemId, value) {
        quantities = { ...quantities, [itemId]: value };
        clearTimeout(debounceTimers[itemId]);
        debounceTimers[itemId] = setTimeout(async () => {
            await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
        }, 400);
    }

    onMount(() => {
        // If auth is already resolved at mount time and user is not logged in, redirect immediately.
        // Otherwise $effect below handles the async case (user.loading was true at mount).
        if (!user.loading && !user.isLoggedIn) {
            goto('/auth');
        }
    });

    // Runs whenever user.loading or user.isLoggedIn changes.
    // Handles the case where auth resolved AFTER mount (slow /me response).
    $effect(() => {
        if (user.loading) return;
        if (!user.isLoggedIn) { goto('/auth'); return; }
        // Load once when user is confirmed logged in and data is absent.
        // `loading` is not read here intentionally — avoids re-triggering
        // while loadData is in flight (allItems.length === 0 stays false after load).
        if (allItems.length === 0) {
            loadData();
        }
    });
</script>

<div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <h1 class="text-2xl font-black tracking-tight">Inventory</h1>

    <!-- Filter bar -->
    <div class="flex flex-col md:flex-row gap-3 sticky top-16 z-10 bg-base-100/80 py-2 backdrop-blur-sm">
        <input
            type="text"
            placeholder="Search items…"
            bind:value={searchQuery}
            class="input input-bordered input-sm md:input-md w-full md:w-64"
        />
        <select class="select select-bordered select-sm md:select-md w-full md:min-w-[180px]" bind:value={selectedCategory}>
            <option value="">All Categories</option>
            {#each CATEGORIES as cat}<option value={cat}>{cat}</option>{/each}
        </select>
        <select class="select select-bordered select-sm md:select-md w-full md:min-w-[150px]" bind:value={selectedGrade}>
            <option value="">All Grades</option>
            {#each GRADES as g}<option value={g}>{g}</option>{/each}
        </select>
    </div>

    {#if loading}
        <div class="flex justify-center py-20">
            <span class="loading loading-dots loading-lg text-primary"></span>
        </div>
    {:else}
        <div class="card bg-base-100 border border-base-200 shadow-sm overflow-x-auto">
            <table class="table table-sm w-full">
                <thead>
                    <tr class="bg-base-200/50">
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Item</th>
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Category</th>
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Grade</th>
                        <th class="text-right text-xs font-mono uppercase tracking-wider opacity-60">Quantity</th>
                    </tr>
                </thead>
                <tbody>
                    {#each filtered as item (item.id)}
                        <tr class="hover:bg-base-200/30">
                            <td class="font-medium">{item.name}</td>
                            <td class="text-xs opacity-60">{item.category}</td>
                            <td>
                                <span class="badge badge-outline badge-xs font-black uppercase"
                                      style="color:{gradeColor(item.grade)};border-color:{gradeColor(item.grade)}55">
                                    {item.grade}
                                </span>
                            </td>
                            <td class="text-right">
                                <input
                                    type="number"
                                    min="0"
                                    value={quantities[item.id] ?? ''}
                                    placeholder="0"
                                    oninput={(e) => {
                                        const v = parseInt(/** @type {HTMLInputElement} */(e.target).value);
                                        handleQuantityChange(item.id, isNaN(v) ? 0 : v);
                                    }}
                                    class="input input-xs input-bordered w-24 text-right font-mono tabular-nums"
                                />
                            </td>
                        </tr>
                    {/each}
                    {#if filtered.length === 0}
                        <tr>
                            <td colspan="4" class="text-center py-8 opacity-40 text-sm font-mono">No items match filters</td>
                        </tr>
                    {/if}
                </tbody>
            </table>
        </div>
        <div class="text-center text-[10px] opacity-20 font-bold uppercase pb-4">
            {filtered.length} / {allItems.length} items
        </div>
    {/if}
</div>
```

- [ ] **Step 2: Add Inventory link in navbar**

In `frontend/src/routes/+layout.svelte`, find the `{#if user.isLoggedIn}` block in the nav links. Add `Inventory` next to `Watchlist`:

```svelte
<li>
    <a href="/inventory" class="font-semibold text-sm hover:text-primary transition-colors">
        Inventory
    </a>
</li>
```

- [ ] **Step 3: Verify svelte-check**

```bash
cd /home/dv6/GitHub/improved-octo-potato/frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```

Expected: `0 errors`

- [ ] **Step 4: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add frontend/src/routes/inventory/ frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): /inventory page + navbar link"
```

---

## Task 5: Frontend — RecipeTree integration (replace localStorage)

**Files:**
- Modify: `frontend/src/routes/items/[id]/+page.svelte`
- Modify: `frontend/src/lib/components/crafting/RecipeCard.svelte`

- [ ] **Step 1: Add `user` import to +page.svelte**

In `frontend/src/routes/items/[id]/+page.svelte`, add to the existing imports block:
```js
    import { user } from '$lib/auth.svelte.js';
```

- [ ] **Step 2: Replace `loadCraftTree` to also fetch inventory when logged in**

Find the current `loadCraftTree` function and replace it with:

```js
    async function loadCraftTree() {
        try {
            const r = await fetch(`${API_BASE_URL}/crafting/${getItemId()}/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ multiplier: 1, inventory: {} }),
            });
            if (r.status === 404) { hasRecipe = false; return; }
            if (!r.ok) return;
            craftTree = await r.json();
            hasRecipe = true;

            if (user.isLoggedIn) {
                try {
                    const inv = await fetch(
                        `${API_BASE_URL}/inventory/for-recipe/${getItemId()}`,
                        { credentials: 'include' }
                    );
                    if (inv.ok) {
                        // JSON keys from dict[int, int] are strings — coerce to numbers
                        const raw = await inv.json();
                        inventory = Object.fromEntries(
                            Object.entries(raw).map(([k, v]) => [Number(k), v])
                        );
                    }
                } catch { /* inventory stays empty */ }
            } else {
                inventory = {};
            }
        } catch { hasRecipe = false; }
    }
```

- [ ] **Step 3: Replace `handleSetInventory`**

Find `handleSetInventory` and replace it with the version below. Also remove `handleInventoryUpdate` entirely — it is no longer used.

```js
    /** @param {number} itemId @param {number} value */
    async function handleSetInventory(itemId, value) {
        // Optimistic local update
        const next = { ...inventory };
        if (value > 0) next[itemId] = value;
        else delete next[itemId];
        inventory = next;

        if (!user.isLoggedIn) return;
        try {
            await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
        } catch { /* optimistic update stays */ }
    }
```

- [ ] **Step 4: Remove `onInventoryUpdate` prop from RecipeCard call**

In `+page.svelte`, find the `<RecipeCard>` usage and remove `onInventoryUpdate={handleInventoryUpdate}` (or any `onInventoryUpdate` prop binding) from it.

- [ ] **Step 5: Remove `onInventoryUpdate` from RecipeCard.svelte**

In `frontend/src/lib/components/crafting/RecipeCard.svelte`:

1. Remove `onInventoryUpdate` from the `@type` JSDoc comment on props.
2. Remove `onInventoryUpdate` from the `let { ... } = $props()` destructuring.

RecipeCard no longer calls back to the parent with full inventory — per-item updates go directly to the API from `handleSetInventory` in `+page.svelte`.

- [ ] **Step 6: Remove any localStorage references**

Search for and remove any remaining `localStorage.getItem`, `localStorage.setItem`, or `localStorage.removeItem` calls related to inventory in `+page.svelte`. There should be none after step 3, but verify.

```bash
grep -n "localStorage" /home/dv6/GitHub/improved-octo-potato/frontend/src/routes/items/\[id\]/+page.svelte
```

Expected: no output.

- [ ] **Step 7: Verify svelte-check**

```bash
cd /home/dv6/GitHub/improved-octo-potato/frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```

Expected: `0 errors`

- [ ] **Step 8: Run full test suite**

```bash
cd /home/dv6/GitHub/improved-octo-potato && make test 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add frontend/src/routes/items/[id]/+page.svelte frontend/src/lib/components/crafting/RecipeCard.svelte
git commit -m "feat(frontend): recipe tree uses inventory API, localStorage removed"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| `UserInventory` table with unique constraint | Task 1 |
| Alembic migration | Task 1 |
| `GET /api/inventory` — only rows where qty > 0 | Task 3 (get_inventory only reads existing rows; 0-rows are deleted) |
| `PUT /api/inventory/{item_id}` — upsert, delete on 0 | Task 3 |
| `GET /api/inventory/for-recipe/{item_id}` | Task 3 |
| All endpoints require auth → 401 | Task 3 (current_user dep) + Task 2 tests |
| Unknown item → 404 | Task 3 (NotFoundError) + Task 2 test |
| Negative quantity → 422 | Task 3 (Field(ge=0)) + Task 2 test |
| `/inventory` page with search + category + grade filter | Task 4 |
| Auto-save debounced 400ms | Task 4 |
| Navbar link, auth-gated | Task 4 |
| RecipeTree "Have" pre-filled from API when logged in | Task 5 |
| Changes in "Have" call `PUT /api/inventory` | Task 5 |
| Not logged in → inventory empty, no persistence | Task 5 |
| localStorage removed | Task 5 |

**TDD flow:**
- Task 2: tests written → confirmed RED
- Task 3: implementation → confirmed GREEN
- Tasks 4–5: svelte-check as compile-time gate; full suite at end of Task 5

**No TBD or placeholders.**

**Type consistency:**
- `InventoryUpsert.quantity: int` → `upsert_inventory(quantity: int)` ✓
- `get_inventory_for_recipe` returns `dict[int, int]` → frontend coerces JSON string keys to `Number` ✓
- `handleSetInventory(itemId: number, value: number)` unchanged from current call site in RecipeTree ✓
- `onInventoryUpdate` removed from RecipeCard props AND removed from page call site in Task 5 ✓
- `db_session` fixture defined locally in `test_inventory.py` (same pattern as `test_user_items.py`) ✓
