# Test Coverage Gaps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix dev DB seed data and add 3 test suites that guard against the source-mismatch regression, document the ingest→price-history pipeline, and cover Discord bot command handlers.

**Architecture:** All backend tests go into existing test files (`test_ingest.py` for round-trip, new `test_consistency.py` for cross-file invariants). Bot handler tests extend `discord_bot/tests/test_prices.py` using `unittest.mock.AsyncMock` to fake `discord.Interaction` — no live Discord needed.

**Tech Stack:** pytest-asyncio, respx, unittest.mock, httpx AsyncClient (ASGI transport for backend tests).

---

## File Structure

```
backend/tests/test_ingest.py          MODIFY — add ingest→price-history round-trip tests
backend/tests/test_consistency.py     CREATE — source invariant: seed.py must use "ah"
discord_bot/tests/test_prices.py      MODIFY — add /addprice and /price handler tests
```

No production code changes. Task 1 is a one-time SQL fix in dev — no file changes.

---

## Task 1: Fix dev DB — update seed data source

**Files:** none (SQL command only)

The dev database has PricePoint rows with `source="market"` from the old seed. The frontend now queries `source="ah"`. Until the data is updated, the price history chart is empty.

- [ ] **Step 1.1: Update existing PricePoint rows**

```bash
podman exec -it $(podman ps -q --filter name=db) \
  psql -U postgres -d app -c \
  "UPDATE pricepoint SET source='ah' WHERE source='market'; SELECT COUNT(*) FROM pricepoint WHERE source='ah';"
```

Expected output: a count > 0 (number of updated rows).

- [ ] **Step 1.2: Verify chart works**

Open `http://localhost:5173`, navigate to any item that has price history, confirm the chart renders data. If no items have price history yet, run:

```bash
make seed
```

Then reload the item page — chart should show 30 days of historical buckets.

---

## Task 2: Backend — ingest → price-history round-trip test

**Files:**
- Modify: `backend/tests/test_ingest.py`

This is the most important regression test: it documents that a price submitted via the bot (`POST /api/ingest/prices`) actually appears on the frontend chart (`GET /price-history?source=ah`).

- [ ] **Step 2.1: Write the failing tests**

Add to the bottom of `backend/tests/test_ingest.py`. The `client` fixture already exists in `conftest.py`:

```python
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

    # Querying with wrong source returns empty — price is NOT visible on wrong chart
    wrong_resp = await client.get(
        f"/api/items/{item_id}/price-history",
        params={"source": "market", "interval": "raw"},
    )
    assert wrong_resp.status_code == 200
    assert wrong_resp.json() == []
```

- [ ] **Step 2.2: Run to confirm they pass**

Prerequisites: PostgreSQL running (see CLAUDE.md).

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend
uv run pytest tests/test_ingest.py::test_ingest_price_appears_in_price_history tests/test_ingest.py::test_ingest_source_ah_does_not_appear_under_wrong_source -v
```

Expected: both PASS. These tests should pass immediately — they test existing correct behavior.

- [ ] **Step 2.3: Run full backend suite to check no regressions**

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend && uv run pytest -v 2>&1 | tail -15
```

Expected: all tests PASS.

- [ ] **Step 2.4: Commit**

```bash
git add backend/tests/test_ingest.py
git commit -m "test(backend): ingest→price-history round-trip with source=ah"
```

---

## Task 3: Backend — source consistency invariant

**Files:**
- Create: `backend/tests/test_consistency.py`

This test acts as a contract: it fails immediately if anyone changes `seed.py` to use a different source without updating the frontend. One line of code, prevents the entire class of source-mismatch bugs.

- [ ] **Step 3.1: Write the failing test**

Create `backend/tests/test_consistency.py`:

```python
"""
Cross-file consistency checks.

These tests guard invariants that span multiple files and would otherwise
only be caught at runtime (e.g. source mismatch between seed data and
frontend chart queries).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_seed_uses_ah_source():
    """seed.py must use source='ah' — the same source the frontend chart queries."""
    seed = (REPO_ROOT / "backend" / "seed.py").read_text()
    assert 'source="ah"' in seed, (
        "seed.py must use source='ah' to match the frontend chart. "
        "Found a different source — update seed.py or frontend/src/routes/items/[id]/+page.svelte."
    )
    assert 'source="market"' not in seed, (
        "seed.py still contains source='market' which the frontend no longer queries."
    )


def test_frontend_chart_uses_ah_source():
    """Frontend price chart must query source='ah' — matching seed and bot."""
    page = (
        REPO_ROOT / "frontend" / "src" / "routes" / "items" / "[id]" / "+page.svelte"
    ).read_text()
    assert "const SOURCE = 'ah'" in page, (
        "Frontend chart SOURCE constant must be 'ah'. "
        "Check frontend/src/routes/items/[id]/+page.svelte."
    )
```

- [ ] **Step 3.2: Run to confirm they pass**

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend && uv run pytest tests/test_consistency.py -v
```

Expected: both PASS. If either fails, fix the source mismatch before committing.

- [ ] **Step 3.3: Commit**

```bash
git add backend/tests/test_consistency.py
git commit -m "test(backend): source consistency invariant — seed and frontend must use source=ah"
```

---

## Task 4: Bot — /addprice and /price command handler tests

**Files:**
- Modify: `discord_bot/tests/test_prices.py`

The command handlers (`addprice`, `price`) are untested — only the pure helper functions are covered. These tests use `unittest.mock.AsyncMock` to fake `discord.Interaction` without touching Discord at all.

- [ ] **Step 4.1: Write the tests**

Append to `discord_bot/tests/test_prices.py`:

```python
from unittest.mock import AsyncMock, MagicMock


# ── Interaction mock helper ───────────────────────────────────────────────────

def make_interaction() -> MagicMock:
    """Return a minimal fake discord.Interaction for command handler tests."""
    interaction = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def last_message(interaction: MagicMock) -> str:
    """Return the first positional arg of the last followup.send call."""
    return interaction.followup.send.call_args.args[0]


# ── /addprice handler ─────────────────────────────────────────────────────────

async def test_addprice_zero_price_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice(interaction, name="Egg", gold=0, silver=0, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    assert "zero" in last_message(interaction).lower()


async def test_addprice_negative_gold_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice(interaction, name="Egg", gold=-1, silver=0, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    assert "negative" in last_message(interaction).lower()


async def test_addprice_unreasonable_price_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice(
        interaction, name="Egg", gold=1_000_000, silver=0, copper=0, grade=0
    )

    interaction.followup.send.assert_called_once()
    assert "high" in last_message(interaction).lower()


@respx.mock
async def test_addprice_item_not_found_sends_not_found():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={"items": [], "total": 0, "offset": 0, "limit": 20},
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice(interaction, name="Nonexistent", gold=5, silver=0, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    assert "not found" in last_message(interaction).lower()


@respx.mock
async def test_addprice_success_sends_saved_message():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )
    respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200, json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []}
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice(interaction, name="Iron Ore", gold=3, silver=20, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    msg = last_message(interaction)
    assert "saved" in msg.lower()
    assert "3g" in msg
    assert "20s" in msg


# ── /price handler ────────────────────────────────────────────────────────────

@respx.mock
async def test_price_item_not_found_sends_not_found():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={"items": [], "total": 0, "offset": 0, "limit": 20},
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price(interaction, name="Nonexistent", grade=0)

    interaction.followup.send.assert_called_once()
    assert "not found" in last_message(interaction).lower()


@respx.mock
async def test_price_no_price_yet_sends_use_addprice():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price(interaction, name="Iron Ore", grade=0)

    interaction.followup.send.assert_called_once()
    assert "addprice" in last_message(interaction).lower()


@respx.mock
async def test_price_shows_formatted_price():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": 32000,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price(interaction, name="Iron Ore", grade=0)

    interaction.followup.send.assert_called_once()
    msg = last_message(interaction)
    assert "3g" in msg
    assert "20s" in msg
```

- [ ] **Step 4.2: Run tests to confirm they pass**

```bash
cd /home/dv6/GitHub/improved-octo-potato/discord_bot && uv run pytest tests/ -v 2>&1 | tail -25
```

Expected: all 21 tests PASS (13 existing + 8 new).

- [ ] **Step 4.3: Run ruff**

```bash
cd /home/dv6/GitHub/improved-octo-potato/discord_bot && uv run ruff check . && uv run ruff format --check .
```

Expected: no errors.

- [ ] **Step 4.4: Commit**

```bash
git add discord_bot/tests/test_prices.py
git commit -m "test(discord-bot): /addprice and /price command handler tests"
```

---

## Task 5: Push and verify CI

- [ ] **Step 5.1: Run full test suites locally**

```bash
cd /home/dv6/GitHub/improved-octo-potato/backend && uv run pytest -v 2>&1 | tail -5
cd /home/dv6/GitHub/improved-octo-potato/discord_bot && uv run pytest -v 2>&1 | tail -5
```

Expected: backend all pass, bot all pass.

- [ ] **Step 5.2: Push**

```bash
git push origin discord-bot
```

Expected: CI green on GitHub for both `backend` and `discord-bot` workflows.
