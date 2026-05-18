import os
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.items.models import Item, ItemCategory, ItemGrade
from app.ingest.schemas import IngestRequest, PriceIngestRow
from app.ingest.services import bulk_ingest, match_or_create_item

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


async def test_match_or_create_returns_existing_item(db_session: AsyncSession):
    existing = Item(
        name="Egg", category=ItemCategory.CONSUMABLES, grade=ItemGrade.GRAND
    )
    db_session.add(existing)
    await db_session.commit()
    await db_session.refresh(existing)

    item, created = await match_or_create_item(
        db_session, name="Egg", grade=ItemGrade.GRAND
    )

    assert created is False
    assert item.id == existing.id


async def test_match_or_create_creates_when_missing(db_session: AsyncSession):
    item, created = await match_or_create_item(
        db_session, name="Unknown Thing", grade=ItemGrade.RARE
    )

    assert created is True
    assert item.id is not None
    assert item.name == "Unknown Thing"
    assert item.grade == ItemGrade.RARE
    assert item.category == ItemCategory.OTHER


async def test_bulk_ingest_creates_pricepoint_for_existing_item(
    db_session: AsyncSession,
):
    item = Item(name="Egg", category=ItemCategory.CONSUMABLES, grade=ItemGrade.GRAND)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Egg",
                grade=1,
                price=15000,
                ts=datetime.now(timezone.utc),
                source="ah",
            ),
        ]
    )
    report = await bulk_ingest(db_session, req)

    assert report.accepted == 1
    assert report.auto_created == 0
    assert report.skipped == 0
    assert report.errors == []


async def test_bulk_ingest_auto_creates_unknown_item(db_session: AsyncSession):
    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Fresh New Item",
                grade=2,
                price=42,
                ts=datetime.now(timezone.utc),
                source="ah",
            ),
        ]
    )
    report = await bulk_ingest(db_session, req)

    assert report.accepted == 1
    assert report.auto_created == 1

    result = await db_session.exec(select(Item).where(Item.name == "Fresh New Item"))
    created = result.first()
    assert created is not None
    assert created.grade == ItemGrade.RARE
    assert created.category == ItemCategory.OTHER


async def test_bulk_ingest_skips_future_ts(db_session: AsyncSession):
    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Good",
                grade=1,
                price=100,
                ts=datetime.now(timezone.utc),
                source="ah",
            ),
            PriceIngestRow(
                name="Bad",
                grade=1,
                price=100,
                ts=datetime.now(timezone.utc) + timedelta(hours=2),
                source="ah",
            ),
        ]
    )
    report = await bulk_ingest(db_session, req)

    assert report.accepted == 1
    assert report.skipped == 1
    assert len(report.errors) == 1
    assert report.errors[0].row_index == 1
    assert "future" in report.errors[0].reason.lower()


async def test_bulk_ingest_empty_batch(db_session: AsyncSession):
    req = IngestRequest(rows=[])
    report = await bulk_ingest(db_session, req)
    assert report.accepted == 0
    assert report.auto_created == 0
    assert report.skipped == 0
    assert report.errors == []


async def test_bulk_ingest_match_by_name_and_grade(db_session: AsyncSession):
    grand = Item(name="Sword", category=ItemCategory.WEAPONS, grade=ItemGrade.GRAND)
    rare = Item(name="Sword", category=ItemCategory.WEAPONS, grade=ItemGrade.RARE)
    db_session.add(grand)
    db_session.add(rare)
    await db_session.commit()
    await db_session.refresh(grand)
    await db_session.refresh(rare)

    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Sword",
                grade=2,
                price=500,
                ts=datetime.now(timezone.utc),
                source="ah",
            ),
        ]
    )
    report = await bulk_ingest(db_session, req)

    assert report.accepted == 1
    assert report.auto_created == 0
    from app.prices.models import PricePoint

    points = (
        await db_session.exec(select(PricePoint).where(PricePoint.item_id == rare.id))
    ).all()
    assert len(points) == 1
    assert points[0].price == 500


async def test_post_ingest_prices_returns_200(client: AsyncClient):
    resp = await client.post(
        "/api/ingest/prices",
        json={
            "rows": [
                {
                    "name": "API Test",
                    "grade": 1,
                    "price": 999,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": "ah",
                }
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 1
    assert body["auto_created"] == 1


async def test_post_ingest_rejects_batch_over_100(client: AsyncClient):
    rows = [
        {
            "name": f"i{n}",
            "grade": 1,
            "price": 1,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "ah",
        }
        for n in range(101)
    ]
    resp = await client.post("/api/ingest/prices", json={"rows": rows})
    assert resp.status_code == 422


async def test_post_ingest_rejects_invalid_grade(client: AsyncClient):
    resp = await client.post(
        "/api/ingest/prices",
        json={
            "rows": [
                {
                    "name": "X",
                    "grade": 99,
                    "price": 1,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": "ah",
                }
            ]
        },
    )
    assert resp.status_code == 422


async def test_post_ingest_rejects_negative_price(client: AsyncClient):
    resp = await client.post(
        "/api/ingest/prices",
        json={
            "rows": [
                {
                    "name": "X",
                    "grade": 1,
                    "price": -1,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": "ah",
                }
            ]
        },
    )
    assert resp.status_code == 422


async def test_post_ingest_partial_success_reports_skipped(client: AsyncClient):
    rows = [
        {
            "name": "Good",
            "grade": 1,
            "price": 100,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "ah",
        },
        {
            "name": "Future",
            "grade": 1,
            "price": 100,
            "ts": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
            "source": "ah",
        },
    ]
    resp = await client.post("/api/ingest/prices", json={"rows": rows})
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 1
    assert body["skipped"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row_index"] == 1


async def test_bulk_ingest_accepts_grade_zero_basic(db_session: AsyncSession):
    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Iron Ore",
                grade=0,
                price=32000,
                ts=datetime.now(timezone.utc),
                source="discord",
            )
        ]
    )
    report = await bulk_ingest(db_session, req)
    assert report.accepted == 1
    assert report.auto_created == 1


async def test_bulk_ingest_grade_zero_creates_item_with_basic_grade(
    db_session: AsyncSession,
):
    req = IngestRequest(
        rows=[
            PriceIngestRow(
                name="Lumber",
                grade=0,
                price=18000,
                ts=datetime.now(timezone.utc),
                source="discord",
            )
        ]
    )
    await bulk_ingest(db_session, req)

    result = await db_session.exec(select(Item).where(Item.name == "Lumber"))
    item = result.first()
    assert item is not None
    assert item.grade == ItemGrade.BASIC


async def test_ingest_price_appears_in_price_history(client: AsyncClient):
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).isoformat()
    ingest_resp = await client.post(
        "/api/ingest/prices",
        json={
            "rows": [
                {
                    "name": "History Test Item",
                    "grade": 0,
                    "price": 50000,
                    "ts": ts,
                    "source": "ah",
                }
            ]
        },
    )
    assert ingest_resp.status_code == 200
    body = ingest_resp.json()
    assert body["accepted"] == 1

    # Find the auto-created item
    items_resp = await client.get("/api/items/", params={"q": "History Test Item"})
    assert items_resp.status_code == 200
    items = items_resp.json()["items"]
    assert len(items) == 1
    item_id = items[0]["id"]

    history_resp = await client.get(
        f"/api/items/{item_id}/price-history",
        params={"source": "ah", "interval": "raw"},
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["price"] == 50000


async def test_ingest_source_ah_does_not_appear_under_wrong_source(
    client: AsyncClient,
):
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).isoformat()
    ingest_resp = await client.post(
        "/api/ingest/prices",
        json={
            "rows": [
                {
                    "name": "Source Isolation Item",
                    "grade": 0,
                    "price": 12345,
                    "ts": ts,
                    "source": "ah",
                }
            ]
        },
    )
    assert ingest_resp.json()["accepted"] == 1

    items_resp = await client.get("/api/items/", params={"q": "Source Isolation Item"})
    item_id = items_resp.json()["items"][0]["id"]

    # Querying with wrong source returns empty
    wrong_resp = await client.get(
        f"/api/items/{item_id}/price-history",
        params={"source": "market", "interval": "raw"},
    )
    assert wrong_resp.status_code == 200
    assert wrong_resp.json() == []
