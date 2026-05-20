# Discord Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discord slash-command bot with `/addprice` and `/price` commands that log AH prices to the backend ingest API, rejecting unknown items with fuzzy suggestions.

**Architecture:** Independent `discord_bot/` Python project (mirrors `watcher/`) added as a Docker compose service. Bot talks to the backend over Docker internal network. Backend gets a new `BASIC` grade and expanded grade map (0-11) before the bot is built.

**Tech Stack:** discord.py 2.x, httpx, pydantic-settings; pytest + respx for bot tests; uv for dependency management.

**Spec:** `docs/superpowers/specs/2026-05-17-discord-bot-design.md`

---

## File Structure

```
backend/app/items/models.py          MODIFY — add BASIC to ItemGrade
backend/app/ingest/grade_map.py      MODIFY — extend to 0-11
backend/app/ingest/schemas.py        MODIFY — ge=0, le=11
backend/tests/test_ingest.py         MODIFY — 2 new tests for grade=0

discord_bot/
  pyproject.toml                     CREATE — uv project, discord.py + httpx + pydantic-settings
  Dockerfile                         CREATE — uv-based, mirrors backend Dockerfile
  bot.py                             CREATE — startup, load cog, sync slash commands
  cogs/__init__.py                   CREATE — empty
  cogs/prices.py                     CREATE — /addprice and /price, lookup/post helpers
  tests/__init__.py                  CREATE — empty
  tests/test_prices.py               CREATE — unit tests for helpers (respx mocks)

infra/compose/docker-compose.dev.yml   MODIFY — add discord_bot service
infra/compose/docker-compose.prod.yml  MODIFY — add discord_bot service
.env.example                           MODIFY — add DISCORD_TOKEN, DISCORD_GUILD_ID
.github/workflows/discord_bot.yml      CREATE — ruff + pytest CI
```

---

## Task 1: Backend — BASIC grade + extended grade map

**Files:**
- Modify: `backend/app/items/models.py`
- Modify: `backend/app/ingest/grade_map.py`
- Modify: `backend/app/ingest/schemas.py`
- Modify: `backend/tests/test_ingest.py`

- [ ] **Step 1.1: Write two failing tests for grade=0**

Add to the bottom of `backend/tests/test_ingest.py`:

```python
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
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_ingest.py::test_bulk_ingest_accepts_grade_zero_basic tests/test_ingest.py::test_bulk_ingest_grade_zero_creates_item_with_basic_grade -v
```

Expected: FAIL — `ItemGrade` has no attribute `BASIC`, schema rejects `grade=0`.

- [ ] **Step 1.3: Add BASIC to ItemGrade**

In `backend/app/items/models.py`, add `BASIC` as the first real grade (after `ALL`):

```python
class ItemGrade(StrEnum):
    ALL = "All"
    BASIC = "Basic"
    GRAND = "Grand"
    RARE = "Rare"
    ARCANE = "Arcane"
    HEROIC = "Heroic"
    UNIQUE = "Unique"
    CELESTIAL = "Celestial"
    DIVINE = "Divine"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"
    ETERNAL = "Eternal"
```

- [ ] **Step 1.4: Extend grade_map.py to 0-11**

Replace the entire content of `backend/app/ingest/grade_map.py`:

```python
from app.items.models import ItemGrade

# Integer grades used by the ingest API (0 = Basic, 1-6 = game grades, 7-11 = high-end).
GAME_GRADE_TO_ENUM: dict[int, ItemGrade] = {
    0: ItemGrade.BASIC,
    1: ItemGrade.GRAND,
    2: ItemGrade.RARE,
    3: ItemGrade.ARCANE,
    4: ItemGrade.HEROIC,
    5: ItemGrade.UNIQUE,
    6: ItemGrade.CELESTIAL,
    7: ItemGrade.DIVINE,
    8: ItemGrade.EPIC,
    9: ItemGrade.LEGENDARY,
    10: ItemGrade.MYTHIC,
    11: ItemGrade.ETERNAL,
}


def map_grade(game_grade: int) -> ItemGrade | None:
    return GAME_GRADE_TO_ENUM.get(game_grade)
```

- [ ] **Step 1.5: Extend ingest schema to accept grades 0-11**

In `backend/app/ingest/schemas.py`, change the `grade` field:

```python
grade: int = Field(ge=0, le=11)
```

- [ ] **Step 1.6: Run tests — must pass**

```bash
cd backend && uv run pytest tests/test_ingest.py -v
```

Expected: all tests PASS. (No migration needed — ItemGrade is stored as VARCHAR, adding a Python enum value does not change the DB schema.)

- [ ] **Step 1.7: Commit**

```bash
git add backend/app/items/models.py backend/app/ingest/grade_map.py backend/app/ingest/schemas.py backend/tests/test_ingest.py
git commit -m "feat(backend): add BASIC grade, extend grade map 0-11"
```

---

## Task 2: Bot scaffold — pyproject.toml, Dockerfile, bot.py

**Files:**
- Create: `discord_bot/pyproject.toml`
- Create: `discord_bot/Dockerfile`
- Create: `discord_bot/bot.py`
- Create: `discord_bot/cogs/__init__.py`

- [ ] **Step 2.1: Create pyproject.toml**

Create `discord_bot/pyproject.toml`:

```toml
[project]
name = "discord-bot"
version = "0.1.0"
description = "Discord slash-command bot for AH price entry"
requires-python = ">=3.13"
dependencies = [
    "discord.py>=2.4",
    "httpx>=0.27",
    "pydantic-settings>=2.3",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.15",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2.2: Install dependencies**

```bash
cd discord_bot && uv sync
```

Expected: `discord_bot/.venv/` created, no errors.

- [ ] **Step 2.3: Create Dockerfile**

Create `discord_bot/Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-cache --no-dev

COPY bot.py ./
COPY cogs ./cogs

CMD ["uv", "run", "python", "bot.py"]
```

- [ ] **Step 2.4: Create bot.py**

Create `discord_bot/bot.py`:

```python
import asyncio
import logging

import discord
from discord.ext import commands
from pydantic import Field
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_GUILD_ID: int | None = None
    API_URL: str = "http://backend:8000/api"


settings = Settings()


class PriceBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.prices")
        if settings.DISCORD_GUILD_ID:
            guild = discord.Object(id=settings.DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Slash commands synced to guild %s", settings.DISCORD_GUILD_ID)
        else:
            await self.tree.sync()
            logging.info("Slash commands synced globally")

    async def on_ready(self) -> None:
        logging.info("Logged in as %s (id=%s)", self.user, self.user.id)


bot = PriceBot()
bot.api_url = settings.API_URL


if __name__ == "__main__":
    asyncio.run(bot.start(settings.DISCORD_TOKEN))
```

- [ ] **Step 2.5: Create cogs/__init__.py**

Create `discord_bot/cogs/__init__.py` as an empty file.

- [ ] **Step 2.6: Commit**

```bash
git add discord_bot/
git commit -m "feat(discord-bot): scaffold — pyproject, Dockerfile, bot.py"
```

---

## Task 3: Prices cog — helpers and slash commands

**Files:**
- Create: `discord_bot/cogs/prices.py`

- [ ] **Step 3.1: Create prices.py**

Create `discord_bot/cogs/prices.py`:

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
import httpx
from discord import Interaction, app_commands
from discord.ext import commands

GRADE_CHOICES = [
    app_commands.Choice(name="basic", value=0),
    app_commands.Choice(name="grand", value=1),
    app_commands.Choice(name="rare", value=2),
    app_commands.Choice(name="arcane", value=3),
    app_commands.Choice(name="heroic", value=4),
    app_commands.Choice(name="unique", value=5),
    app_commands.Choice(name="celestial", value=6),
    app_commands.Choice(name="divine", value=7),
    app_commands.Choice(name="epic", value=8),
    app_commands.Choice(name="legendary", value=9),
    app_commands.Choice(name="mythic", value=10),
    app_commands.Choice(name="eternal", value=11),
]

# Map int grade (0-11) to the ItemGrade string value stored in the DB.
GRADE_INT_TO_STR: dict[int, str] = {c.value: c.name.capitalize() for c in GRADE_CHOICES}


def format_price(copper: int) -> str:
    """Return copper amount as human-readable gold/silver/copper string."""
    g = copper // 10000
    s = (copper % 10000) // 100
    c = copper % 100
    parts = []
    if g:
        parts.append(f"{g}g")
    if s:
        parts.append(f"{s}s")
    if c or not parts:
        parts.append(f"{c}c")
    return " ".join(parts)


async def lookup_item(
    api_url: str, name: str, grade_int: int
) -> tuple[dict | None, list[str]]:
    """Search backend for item by name+grade.

    Returns (item_dict, []) on exact match, or (None, suggestions) if not found.
    suggestions is a list of up to 5 unique item names from the search results.
    Raises httpx.HTTPError on network/backend failure.
    """
    grade_str = GRADE_INT_TO_STR[grade_int]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{api_url}/items/", params={"q": name, "limit": 20})
        resp.raise_for_status()

    items: list[dict] = resp.json()["items"]

    exact = next(
        (i for i in items if i["name"].lower() == name.lower() and i["grade"] == grade_str),
        None,
    )
    if exact is not None:
        return exact, []

    seen: set[str] = set()
    suggestions: list[str] = []
    for item in items:
        n = item["name"]
        if n not in seen:
            seen.add(n)
            suggestions.append(n)
            if len(suggestions) == 5:
                break
    return None, suggestions


async def post_price(api_url: str, name: str, grade_int: int, price_copper: int) -> None:
    """POST one price row to the ingest API.

    Raises httpx.HTTPError on failure.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    payload = {
        "rows": [
            {
                "name": name,
                "grade": grade_int,
                "price": price_copper,
                "ts": ts,
                "source": "discord",
            }
        ]
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{api_url}/ingest/prices", json=payload)
        resp.raise_for_status()


class PricesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addprice", description="Dodaj cene przedmiotu z AH")
    @app_commands.describe(
        name="Nazwa przedmiotu (dokladna, np. Iron Ore)",
        grade="Grade przedmiotu (domyslnie: basic)",
        gold="Zloto",
        silver="Srebro",
        copper="Miedz",
    )
    @app_commands.choices(grade=GRADE_CHOICES)
    async def addprice(
        self,
        interaction: Interaction,
        name: str,
        gold: int = 0,
        silver: int = 0,
        copper: int = 0,
        grade: int = 0,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        total = gold * 10000 + silver * 100 + copper
        if total == 0:
            await interaction.followup.send("Cena nie moze byc zerowa.", ephemeral=True)
            return

        try:
            item, suggestions = await lookup_item(self.bot.api_url, name, grade)
        except httpx.HTTPError:
            logging.exception("Backend unreachable in /addprice")
            await interaction.followup.send(
                "Blad polaczenia z backendem — sprobuj za chwile.", ephemeral=True
            )
            return

        if item is None:
            grade_name = GRADE_INT_TO_STR[grade].lower()
            msg = f'Nie znaleziono "{name}" (grade: {grade_name}).'
            if suggestions:
                msg += f"\nPodobne: {', '.join(suggestions)}"
            await interaction.followup.send(msg, ephemeral=True)
            return

        try:
            await post_price(self.bot.api_url, item["name"], grade, total)
        except httpx.HTTPError:
            logging.exception("Backend unreachable posting price in /addprice")
            await interaction.followup.send(
                "Blad polaczenia z backendem — sprobuj za chwile.", ephemeral=True
            )
            return

        grade_name = GRADE_INT_TO_STR[grade].lower()
        await interaction.followup.send(
            f'{item["name"]} ({grade_name}): {format_price(total)} zapisane.',
            ephemeral=True,
        )

    @app_commands.command(name="price", description="Sprawdz aktualna cene przedmiotu")
    @app_commands.describe(
        name="Nazwa przedmiotu",
        grade="Grade przedmiotu (domyslnie: basic)",
    )
    @app_commands.choices(grade=GRADE_CHOICES)
    async def price(
        self,
        interaction: Interaction,
        name: str,
        grade: int = 0,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            item, suggestions = await lookup_item(self.bot.api_url, name, grade)
        except httpx.HTTPError:
            logging.exception("Backend unreachable in /price")
            await interaction.followup.send(
                "Blad polaczenia z backendem — sprobuj za chwile.", ephemeral=True
            )
            return

        grade_name = GRADE_INT_TO_STR[grade].lower()

        if item is None:
            msg = f'Nie znaleziono "{name}" (grade: {grade_name}).'
            if suggestions:
                msg += f"\nPodobne: {', '.join(suggestions)}"
            await interaction.followup.send(msg, ephemeral=True)
            return

        current = item.get("current_price")
        if current is None:
            await interaction.followup.send(
                f'{item["name"]} ({grade_name}): brak ceny — uzyj /addprice',
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f'{item["name"]} ({grade_name}): {format_price(current)}',
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PricesCog(bot))
```

- [ ] **Step 3.2: Commit**

```bash
git add discord_bot/cogs/
git commit -m "feat(discord-bot): prices cog — /addprice and /price slash commands"
```

---

## Task 4: Bot tests

**Files:**
- Create: `discord_bot/tests/__init__.py`
- Create: `discord_bot/tests/test_prices.py`

- [ ] **Step 4.1: Write failing tests**

Create `discord_bot/tests/__init__.py` as an empty file.

Create `discord_bot/tests/test_prices.py`:

```python
import pytest
import respx
from httpx import Response

from cogs.prices import format_price, lookup_item, post_price

API_URL = "http://testapi"


# ── format_price ──────────────────────────────────────────────────────────────

def test_format_price_gold_silver_copper():
    assert format_price(32000) == "3g 20s"


def test_format_price_zero_shows_0c():
    assert format_price(0) == "0c"


def test_format_price_only_copper():
    assert format_price(75) == "75c"


def test_format_price_exact_gold():
    assert format_price(10000) == "1g"


# ── lookup_item ───────────────────────────────────────────────────────────────

@respx.mock
async def test_lookup_item_returns_exact_match():
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

    item, suggestions = await lookup_item(API_URL, "Iron Ore", 0)

    assert item is not None
    assert item["name"] == "Iron Ore"
    assert suggestions == []


@respx.mock
async def test_lookup_item_returns_suggestions_on_no_match():
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
                    },
                    {
                        "id": 2,
                        "name": "Iron Ore Chunk",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    },
                ],
                "total": 2,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    item, suggestions = await lookup_item(API_URL, "Iron Ores", 0)

    assert item is None
    assert "Iron Ore" in suggestions
    assert "Iron Ore Chunk" in suggestions


@respx.mock
async def test_lookup_item_case_insensitive():
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

    item, suggestions = await lookup_item(API_URL, "iron ore", 0)

    assert item is not None
    assert item["name"] == "Iron Ore"


# ── post_price ────────────────────────────────────────────────────────────────

@respx.mock
async def test_post_price_sends_correct_payload():
    route = respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200,
            json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []},
        )
    )

    await post_price(API_URL, "Iron Ore", 0, 32000)

    assert route.called
    body = route.calls[0].request.read()
    import json
    payload = json.loads(body)
    assert payload["rows"][0]["name"] == "Iron Ore"
    assert payload["rows"][0]["grade"] == 0
    assert payload["rows"][0]["price"] == 32000
    assert payload["rows"][0]["source"] == "discord"
```

- [ ] **Step 4.2: Run tests to confirm they fail**

```bash
cd discord_bot && uv run pytest tests/ -v
```

Expected: FAIL — `cogs.prices` not yet importable (no `__init__.py` in discord_bot root for import).

- [ ] **Step 4.3: Fix import path**

The tests import `from cogs.prices import ...` — this works when pytest runs from `discord_bot/`. Verify by checking that `discord_bot/cogs/__init__.py` exists (created in Task 2).

```bash
cd discord_bot && uv run pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4.4: Commit**

```bash
git add discord_bot/tests/
git commit -m "test(discord-bot): unit tests for format_price, lookup_item, post_price"
```

---

## Task 5: Infrastructure — compose, .env.example, CI

**Files:**
- Modify: `infra/compose/docker-compose.dev.yml`
- Modify: `infra/compose/docker-compose.prod.yml`
- Modify: `.env.example`
- Create: `.github/workflows/discord_bot.yml`

- [ ] **Step 5.1: Add discord_bot service to dev compose**

In `infra/compose/docker-compose.dev.yml`, add after the `frontend` service block (before `volumes:`):

```yaml
  discord_bot:
    build: ../../discord_bot
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: ${DISCORD_TOKEN:?DISCORD_TOKEN is required}
      DISCORD_GUILD_ID: ${DISCORD_GUILD_ID:-}
      API_URL: http://backend:8000/api
    depends_on:
      - backend
```

- [ ] **Step 5.2: Add discord_bot service to prod compose**

In `infra/compose/docker-compose.prod.yml`, add the same block after the `caddy` service (before `volumes:`):

```yaml
  discord_bot:
    build: ../../discord_bot
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: ${DISCORD_TOKEN:?DISCORD_TOKEN is required}
      DISCORD_GUILD_ID: ${DISCORD_GUILD_ID:-}
      API_URL: http://backend:8000/api
    depends_on:
      - backend
```

- [ ] **Step 5.3: Add vars to .env.example**

Append to `.env.example`:

```
DISCORD_TOKEN=your-bot-token-here
DISCORD_GUILD_ID=your-server-id-here
```

- [ ] **Step 5.4: Create CI workflow**

Create `.github/workflows/discord_bot.yml`:

```yaml
name: discord-bot

on:
  push:
    paths:
      - "discord_bot/**"
      - ".github/workflows/discord_bot.yml"
  pull_request:
    paths:
      - "discord_bot/**"
      - ".github/workflows/discord_bot.yml"

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: discord_bot

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --frozen

      - name: Lint
        run: uv run ruff check . && uv run ruff format --check .

      - name: Test
        run: uv run pytest -v
```

- [ ] **Step 5.5: Commit**

```bash
git add infra/compose/docker-compose.dev.yml infra/compose/docker-compose.prod.yml .env.example .github/workflows/discord_bot.yml
git commit -m "feat(infra): add discord_bot to compose, .env.example, CI workflow"
```

---

## Task 6: Smoke test

**No code changes — verification only.**

- [ ] **Step 6.1: Run backend tests to confirm no regressions**

Prerequisites: PostgreSQL running (see CLAUDE.md).

```bash
cd backend && uv run pytest -v
```

Expected: all tests PASS including the two new grade=0 tests.

- [ ] **Step 6.2: Run bot tests**

```bash
cd discord_bot && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6.3: Run ruff on bot**

```bash
cd discord_bot && uv run ruff check . && uv run ruff format --check .
```

Expected: no errors.

- [ ] **Step 6.4: Manual smoke test (requires Discord token)**

1. Set `DISCORD_TOKEN` and `DISCORD_GUILD_ID` in `.env`
2. `make dev-up`
3. Check `make dev-logs` — should see `Logged in as <bot-name>` and `Slash commands synced to guild <id>`
4. In Discord: `/price name:Iron Ore` → should return current price or "brak ceny"
5. `/addprice name:Iron Ore gold:3 silver:20` → "Iron Ore (basic): 3g 20s zapisane."
6. `/addprice name:Nonexistent Item gold:1` → rejection with suggestions or empty list

- [ ] **Step 6.5: Final commit if smoke test revealed fixes**

```bash
git add -p
git commit -m "fix(discord-bot): smoke test fixes"
```
