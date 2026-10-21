import csv
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlmodel import col, select

from app.market.models import Item, MarketDay
from app.market.services import import_csv
from tests.market.test_import import _base, rewrite_fixture

FIXTURES = Path(__file__).parent / "fixtures"


@dataclass
class Imported:
    suffix: str
    ids: dict[str, int]

    def name(self, base_name: str) -> str:
        return f"{base_name} {self.suffix}"

    def id(self, base_name: str) -> int:
        return self.ids[self.name(base_name)]


@pytest.fixture()
async def imported(session) -> Imported:
    s, base = uuid.uuid4().hex[:8], _base()
    await import_csv(session, "m.csv", rewrite_fixture("market.csv", s, base))
    await import_csv(session, "l.csv", rewrite_fixture("listings.csv", s, base))
    items = (
        await session.exec(select(Item).where(col(Item.name).endswith(f" {s}")))
    ).all()
    return Imported(s, {i.name: i.id for i in items})


async def test_summary_leather_matches_samples(
    client: AsyncClient, imported: Imported
) -> None:
    rows = (await client.get("/api/market/summary")).json()
    row = next(r for r in rows if r["name"] == imported.name("Leather"))
    assert row == {
        "item_id": imported.id("Leather"),
        "name": imported.name("Leather"),
        "day": "2026-10-21",
        "today_avg": 4702,
        "avg_7d": 4902,
        "change_pct": -0.0408,
        "sold_today": 171924,
        "avg_daily_volume": pytest.approx(94566.571, rel=1e-6),
    }


async def test_days_returns_14_oldest_first(
    client: AsyncClient, imported: Imported
) -> None:
    days = (await client.get(f"/api/market/items/{imported.id('Leather')}/days")).json()
    assert len(days) == 14
    assert days[0]["day"] == "2026-10-08"
    assert days[-1] == {
        "day": "2026-10-21",
        "daily_avg": 4702,
        "weekly_avg": 4877,
        "min": 2100,
        "max": 19999,
        "volume": 171924,
    }


async def test_days_limit(client: AsyncClient, imported: Imported) -> None:
    r = await client.get(f"/api/market/items/{imported.id('Leather')}/days?days=3")
    assert [d["day"] for d in r.json()] == ["2026-10-19", "2026-10-20", "2026-10-21"]


async def test_listings_are_newest_scan_by_rank(
    client: AsyncClient, imported: Imported
) -> None:
    with open(FIXTURES / "listings.csv") as f:
        newest = max(
            int(r["scan_id"]) for r in csv.DictReader(f) if r["item"] == "Leather"
        )
    rows = (
        await client.get(f"/api/market/items/{imported.id('Leather')}/listings")
    ).json()
    assert {r["scan_id"] for r in rows} == {newest}
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert rows[0]["status"] == "ok" and rows[0]["unit_price"] > 0


async def test_listing_only_item(client: AsyncClient, imported: Imported) -> None:
    item_id = imported.id("Nonexistent Item")
    items = (await client.get("/api/market/items")).json()
    entry = next(i for i in items if i["id"] == item_id)
    assert (entry["item_type"], entry["item_grade"], entry["last_day"]) == (
        None,
        None,
        None,
    )
    summary = (await client.get("/api/market/summary")).json()
    assert item_id not in {r["item_id"] for r in summary}
    assert (await client.get(f"/api/market/items/{item_id}/days")).json() == []
    listings = (await client.get(f"/api/market/items/{item_id}/listings")).json()
    assert [r["status"] for r in listings] == ["no_result"]


async def test_change_pct_null_when_avg_7d_zero(client: AsyncClient, session) -> None:
    item = Item(name=f"zero-{uuid.uuid4().hex[:8]}")
    session.add(item)
    await session.commit()
    await session.refresh(item)
    today = date(2026, 10, 21)
    for day, weekly in ((today - timedelta(days=1), 0), (today, 5)):
        session.add(
            MarketDay(
                item_id=item.id,
                day=day,
                daily_avg=10,
                weekly_avg=weekly,
                min=1,
                max=20,
                volume=0,
                scan_id=1,
                captured_at=datetime(2026, 10, 21),
            )  # fmt: skip
        )
    await session.commit()
    rows = (await client.get("/api/market/summary")).json()
    row = next(r for r in rows if r["item_id"] == item.id)
    assert (row["avg_7d"], row["change_pct"], row["avg_daily_volume"]) == (0, None, 0)


async def test_unknown_item_404(client: AsyncClient) -> None:
    for path in ("days", "listings"):
        r = await client.get(f"/api/market/items/999999999/{path}")
        assert r.status_code == 404
