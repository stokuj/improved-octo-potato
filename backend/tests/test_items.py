import pytest
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.items.models import Item, ItemCategory, ItemGrade
import os

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture()
async def db_session():
    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def sample_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Test Sword",
        category=ItemCategory.WEAPONS,
        grade=ItemGrade.RARE,
        current_price=5000,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def test_get_items_returns_list(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/api/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


async def test_get_items_filter_by_category(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/api/items/", params={"category": ItemCategory.WEAPONS})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["category"] == ItemCategory.WEAPONS for i in items)


async def test_get_items_filter_by_name(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/api/items/", params={"q": "Test Sword"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(i["name"] == "Test Sword" for i in data["items"])


async def test_get_item_by_id(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get(f"/api/items/{sample_item.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Sword"


async def test_get_item_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/items/99999999")
    assert resp.status_code == 404


async def test_get_items_filter_by_grade(client: AsyncClient, db_session: AsyncSession) -> None:
    rare = Item(name="Grade Rare Item", category=ItemCategory.ARMOR, grade=ItemGrade.RARE)
    heroic = Item(name="Grade Heroic Item", category=ItemCategory.ARMOR, grade=ItemGrade.HEROIC)
    db_session.add_all([rare, heroic])
    await db_session.commit()

    resp = await client.get("/api/items/", params={"grade": ItemGrade.HEROIC})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["grade"] == ItemGrade.HEROIC for i in items)
    names = [i["name"] for i in items]
    assert "Grade Heroic Item" in names
    assert "Grade Rare Item" not in names


async def test_get_items_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    for i in range(5):
        db_session.add(Item(name=f"Paginate Item {i:02d}", category=ItemCategory.OTHER, grade=ItemGrade.GRAND))
    await db_session.commit()

    page1 = await client.get("/api/items/", params={"q": "Paginate Item", "limit": 3, "offset": 0})
    page2 = await client.get("/api/items/", params={"q": "Paginate Item", "limit": 3, "offset": 3})
    assert page1.status_code == page2.status_code == 200
    d1, d2 = page1.json(), page2.json()
    assert d1["total"] == 5
    assert len(d1["items"]) == 3
    assert len(d2["items"]) == 2
    # No overlap between pages
    ids1 = {i["id"] for i in d1["items"]}
    ids2 = {i["id"] for i in d2["items"]}
    assert ids1.isdisjoint(ids2)
