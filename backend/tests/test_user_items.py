import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.items.models import Item, ItemCategory, ItemGrade
import os

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


def _email() -> str:
    return f"ui-{uuid.uuid4().hex[:8]}@test.com"


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
async def tracked_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Tracked Item",
        category=ItemCategory.ARMOR,
        grade=ItemGrade.HEROIC,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


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


async def test_follow_item_returns_201(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    resp = await auth_client.post(f"/api/user-items/{tracked_item.id}")
    assert resp.status_code == 201


async def test_follow_duplicate_returns_204(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.post(f"/api/user-items/{tracked_item.id}")
    assert resp.status_code == 204


async def test_get_followed_ids_contains_item(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.get("/api/user-items/ids")
    assert resp.status_code == 200
    assert tracked_item.id in resp.json()


async def test_unfollow_item_returns_204(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.delete(f"/api/user-items/{tracked_item.id}")
    assert resp.status_code == 204


async def test_unfollow_removes_from_ids(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    await auth_client.delete(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.get("/api/user-items/ids")
    assert tracked_item.id not in resp.json()


async def test_follow_requires_auth(client: AsyncClient, tracked_item: Item) -> None:
    resp = await client.post(f"/api/user-items/{tracked_item.id}")
    assert resp.status_code == 401
