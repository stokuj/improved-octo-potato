import csv
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlmodel import col, select

from app.market.csv_format import LISTINGS_HEADER_V2, MARKET_HEADER_V2
from app.market.models import Item
from app.market.services import import_csv, min_stack
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
    body = (
        await client.get(f"/api/market/items/{imported.id('Leather')}/listings")
    ).json()
    rows = body["listings"]
    assert body["scan_id"] == newest
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
    assert (entry["min_stack"], entry["cheapest_real"]) == (10, None)
    assert (await client.get(f"/api/market/items/{item_id}/days")).json() == []
    listings = (await client.get(f"/api/market/items/{item_id}/listings")).json()
    assert [r["status"] for r in listings["listings"]] == ["no_result"]


async def test_unknown_item_404(client: AsyncClient) -> None:
    for path in ("days", "listings"):
        r = await client.get(f"/api/market/items/999999999/{path}")
        assert r.status_code == 404


T0 = 1792607894  # 2026-10-21 MSK


def v2_market(
    name: str, item_type: int, category: str, volumes: list[int], captured_at: int
) -> bytes:
    """One row per day, oldest first, ending at day 14; daily/weekly avg 5000."""
    rows = [
        f"{captured_at},{captured_at},{name},{item_type},0,ok,{day},5000,5000,1,9999,{v},{category}"
        for day, v in enumerate(volumes, 15 - len(volumes))
    ]
    return ("\n".join([MARKET_HEADER_V2, *rows]) + "\n").encode()


def v2_listings(
    name: str, item_type: int, offers: list[tuple[int, int]], captured_at: int
) -> bytes:
    """offers = [(stack, unit_price), ...] as ranks 1..n, grade 0."""
    rows = [
        f"{captured_at},{captured_at},{name},ok,{rank},{price},{price * stack},{stack},{item_type},0"
        for rank, (stack, price) in enumerate(offers, 1)
    ]
    return ("\n".join([LISTINGS_HEADER_V2, *rows]) + "\n").encode()


async def _item(client: AsyncClient, name: str) -> dict:
    return next(
        i for i in (await client.get("/api/market/items")).json() if i["name"] == name
    )


async def _with_history(session) -> tuple[str, int]:
    name, t = f"Hide {uuid.uuid4().hex[:8]}", _base()
    # 7 days of 100_000 then today 5_000 -> avg 100_000 -> min_stack 200
    await import_csv(
        session, "m.csv", v2_market(name, t, "Hide", [100_000] * 7 + [5_000], T0)
    )
    offers = [(2, 2165), (150, 4000), (520, 4965)]
    await import_csv(session, "l.csv", v2_listings(name, t, offers, T0))
    return name, t


async def test_items_carry_category_min_stack_and_cheapest_real(
    client: AsyncClient, session
) -> None:
    name, _ = await _with_history(session)
    row = await _item(client, name)
    assert (row["category"], row["min_stack"], row["cheapest_real"]) == (
        "Hide",
        200,
        4965,
    )
    assert row["scan_at"] is not None and row["last_day"] == "2026-10-21"


async def test_min_stack_floor_without_history(client: AsyncClient, session) -> None:
    name, t = f"Bare {uuid.uuid4().hex[:8]}", _base()
    await import_csv(session, "l.csv", v2_listings(name, t, [(5, 100), (12, 300)], T0))
    row = await _item(client, name)
    assert (row["category"], row["min_stack"], row["cheapest_real"]) == (None, 10, 300)


async def test_only_status_rows_means_no_cheapest_real(
    client: AsyncClient, session
) -> None:
    name, t = f"Gone {uuid.uuid4().hex[:8]}", _base()
    await import_csv(session, "a.csv", v2_listings(name, t, [(50, 100)], T0))
    later = f"{T0 + 60},{T0 + 60},{name},no_result,0,,,,,"
    await import_csv(session, "b.csv", f"{LISTINGS_HEADER_V2}\n{later}\n".encode())
    assert (await _item(client, name))["cheapest_real"] is None


async def test_listings_mark_tiny_and_carry_min_stack(
    client: AsyncClient, session
) -> None:
    name, _ = await _with_history(session)
    item_id = (await _item(client, name))["id"]
    body = (await client.get(f"/api/market/items/{item_id}/listings")).json()
    assert (body["scan_id"], body["min_stack"]) == (T0, 200)
    assert [(r["stack"], r["tiny"]) for r in body["listings"]] == [
        (2, True),
        (150, True),
        (520, False),
    ]


async def test_summary_is_gone(client: AsyncClient) -> None:
    assert (await client.get("/api/market/summary")).status_code == 404


def test_min_stack_formula() -> None:
    assert [min_stack(v) for v in (None, 0, 4_999, 5_001, 100_000)] == [
        10,
        10,
        10,
        11,
        200,
    ]
