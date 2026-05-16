import pytest
from datetime import datetime, timezone
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
async def price_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Price Test Item",
        category=ItemCategory.CONSUMABLES,
        grade=ItemGrade.GRAND,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def test_post_price_point_returns_201(client: AsyncClient, price_item: Item) -> None:
    resp = await client.post(
        f"/api/items/{price_item.id}/prices",
        json={
            "source": "market",
            "price": 12345,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == 12345
    assert data["source"] == "market"


async def test_post_price_updates_current_price(
    client: AsyncClient, price_item: Item, db_session: AsyncSession
) -> None:
    await client.post(
        f"/api/items/{price_item.id}/prices",
        json={
            "source": "market",
            "price": 99999,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    # Fresh session avoids stale transaction snapshot from price_item fixture session
    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
    try:
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_maker() as verify_session:
            refreshed = await verify_session.get(Item, price_item.id)
            assert refreshed is not None
            assert refreshed.current_price == 99999
    finally:
        await engine.dispose()


async def test_post_price_for_missing_item_returns_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/items/99999999/prices",
        json={
            "source": "market",
            "price": 100,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 404


async def test_get_price_history_raw(client: AsyncClient, price_item: Item) -> None:
    await client.post(
        f"/api/items/{price_item.id}/prices",
        json={
            "source": "auction",
            "price": 500,
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    resp = await client.get(
        f"/api/items/{price_item.id}/price-history",
        params={"source": "auction", "interval": "raw"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["price"] == 500


async def test_get_price_history_1h_buckets(client: AsyncClient, price_item: Item) -> None:
    # Two points in the same hour bucket, one in a different hour
    for ts, price in [
        ("2026-03-01T10:05:00Z", 1000),
        ("2026-03-01T10:45:00Z", 2000),  # same bucket as above
        ("2026-03-01T11:10:00Z", 3000),  # next bucket
    ]:
        await client.post(
            f"/api/items/{price_item.id}/prices",
            json={"source": "market", "price": price, "captured_at": ts},
        )

    resp = await client.get(
        f"/api/items/{price_item.id}/price-history",
        params={"source": "market", "interval": "1h"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    # Points at 10:05 and 10:45 land in the 10:00 bucket; 11:10 in 11:00 bucket
    hour10 = next(b for b in buckets if "T10:00:00" in b["bucket_start"])
    assert hour10["min_price"] == 1000
    assert hour10["max_price"] == 2000
    assert hour10["avg_price"] == 1500.0
    assert hour10["last_price"] == 2000
    hour11 = next(b for b in buckets if "T11:00:00" in b["bucket_start"])
    assert hour11["min_price"] == hour11["max_price"] == hour11["last_price"] == 3000


async def test_get_price_history_1d_buckets(client: AsyncClient, price_item: Item) -> None:
    for ts, price in [
        ("2026-03-01T08:00:00Z", 100),
        ("2026-03-01T20:00:00Z", 200),
        ("2026-03-02T08:00:00Z", 300),
    ]:
        await client.post(
            f"/api/items/{price_item.id}/prices",
            json={"source": "daily", "price": price, "captured_at": ts},
        )

    resp = await client.get(
        f"/api/items/{price_item.id}/price-history",
        params={"source": "daily", "interval": "1d"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert len(buckets) == 2
    day1 = buckets[0]
    assert "2026-03-01" in day1["bucket_start"]
    assert day1["min_price"] == 100
    assert day1["max_price"] == 200
    assert day1["last_price"] == 200


async def test_get_price_history_date_filter(client: AsyncClient, price_item: Item) -> None:
    for ts, price in [
        ("2026-01-01T00:00:00Z", 111),
        ("2026-06-01T00:00:00Z", 222),
        ("2026-12-01T00:00:00Z", 333),
    ]:
        await client.post(
            f"/api/items/{price_item.id}/prices",
            json={"source": "filter_test", "price": price, "captured_at": ts},
        )

    resp = await client.get(
        f"/api/items/{price_item.id}/price-history",
        params={
            "source": "filter_test",
            "interval": "raw",
            "from": "2026-03-01T00:00:00Z",
            "to": "2026-09-01T00:00:00Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    prices = [p["price"] for p in data]
    assert len(data) == 1
    assert 222 in prices
    assert 111 not in prices
    assert 333 not in prices


async def test_get_price_history_empty_returns_empty_list(
    client: AsyncClient, price_item: Item
) -> None:
    resp = await client.get(
        f"/api/items/{price_item.id}/price-history",
        params={"source": "nosource", "interval": "raw"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_price_history_item_not_found(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/items/99999999/price-history",
        params={"source": "market", "interval": "raw"},
    )
    assert resp.status_code == 404
