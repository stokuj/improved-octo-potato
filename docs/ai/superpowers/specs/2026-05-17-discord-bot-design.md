# discord_bot — design spec

**Status:** approved
**Date:** 2026-05-17
**Goal:** Discord slash-command bot for manual AH price entry. Single user, no auth. Two commands: add a price, query current price.

---

## Problem

The Lua addon UI is unreliable across game updates. A Discord bot lets the user log AH prices manually via slash commands from any device, without touching the game client.

---

## Architecture

New directory `discord_bot/` — independent Python project (own `pyproject.toml`, own Dockerfile), mirroring the `watcher/` pattern. Added as a `discord_bot` service in both `docker-compose.dev.yml` and `docker-compose.prod.yml`. Communicates with the backend over the Docker internal network via `API_URL=http://backend:8000/api`.

```
discord_bot/
├── pyproject.toml        (discord.py 2.x, httpx, pydantic-settings)
├── Dockerfile
├── bot.py                (startup: load cogs, connect to Discord)
└── cogs/
    └── prices.py         (slash commands: /addprice, /price)
```

**Tech stack:** discord.py 2.x (slash commands via app_commands), httpx (async HTTP to backend), pydantic-settings (config).

---

## Configuration

Pydantic-settings with `DISCORD_` prefix, read from root `.env`:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | yes | Bot token from Discord Developer Portal |
| `DISCORD_GUILD_ID` | no | Server ID for instant command sync in dev; omit for global (up to 1h propagation) |
| `API_URL` | yes | Backend base URL — `http://backend:8000/api` in compose |

---

## Backend changes (required before bot works)

### 1. Add `BASIC` grade

`backend/app/items/models.py` — add to `ItemGrade`:

```python
BASIC = "Basic"
```

Alembic migration: `uv run alembic revision --autogenerate -m "add basic item grade"` then `upgrade head`.

### 2. Update grade_map.py

`backend/app/ingest/grade_map.py`:

```python
GAME_GRADE_TO_ENUM: dict[int, ItemGrade] = {
    0: ItemGrade.BASIC,
    1: ItemGrade.GRAND,
    ...
}
```

### 3. Extend ingest schema

`backend/app/ingest/schemas.py`:

```python
grade: int = Field(ge=0, le=6)
```

---

## Commands

### `/addprice name grade gold silver copper`

| Parameter | Type | Required | Default | Notes |
|---|---|---|---|---|
| `name` | string | yes | — | Item name, case-insensitive match |
| `grade` | choice | no | `basic` | One of: basic, grand, rare, arcane, heroic, unique, celestial, divine, epic, legendary, mythic, eternal |
| `gold` | integer | no | 0 | Gold part of price |
| `silver` | integer | no | 0 | Silver part |
| `copper` | integer | no | 0 | Copper part |

**Flow:**
1. Total copper = gold×10000 + silver×100 + copper; if total == 0 → error "Cena nie moze byc zerowa"
2. `GET /api/items/?q=<name>` — look for exact name+grade match (case-insensitive)
3. No exact match → reject, show up to 5 similar items:
   ```
   Nie znaleziono "Iron Ores" (grade: basic).
   Podobne: Iron Ore, Iron Ore Chunk
   ```
4. Exact match found → `POST /api/ingest/prices` with `source="discord"`
5. Success:
   ```
   Iron Ore (basic): 3g 20s 0c zapisane.
   ```

**Example:**
```
/addprice name:Iron Ore gold:3 silver:20
/addprice name:Obsidian Ingot grade:rare gold:15
```

---

### `/price name grade`

| Parameter | Type | Required | Default |
|---|---|---|---|
| `name` | string | yes | — |
| `grade` | choice | no | `basic` |

**Flow:**
1. `GET /api/items/?q=<name>` — exact name+grade match
2. No match → suggestions (same as /addprice)
3. Match found, `current_price` is set → display formatted:
   ```
   Iron Ore (basic): 3g 20s 0c
   ```
4. Match found, `current_price` is null:
   ```
   Iron Ore (basic): brak ceny — uzyj /addprice
   ```

---

## Item matching logic

`GET /api/items/?q=<name>` returns a paginated list. The bot:
1. Searches for an item where `item.name.lower() == name.lower()` and `item.grade == grade`
2. If found → exact match
3. If not found → use the search results as "similar" suggestions (up to 5, show names)

---

## Response style

All responses are **ephemeral** (visible only to the command sender, not the channel). This keeps the channel clean.

Error messages:
- Backend unreachable: `"Blad polaczenia z backendem — sprobuj za chwile"`
- httpx timeout: 10 seconds

---

## Docker integration

`docker-compose.dev.yml` and `docker-compose.prod.yml` — new service:

```yaml
discord_bot:
  build: ./discord_bot
  env_file: .env
  depends_on:
    - backend
  restart: unless-stopped
```

`Makefile` — `make dev-up` starts it automatically with the rest of the stack.

---

## Testing

**Bot (`discord_bot/tests/`):**
- Mock httpx with `respx`
- Test: exact match found → POST sent with correct copper value
- Test: no match → rejection message with suggestions
- Test: backend unreachable → error message

**Backend (`backend/tests/test_ingest.py`):**
- Test: grade=0 accepted, mapped to BASIC
- Test: grade=0 item auto-created with BASIC grade

---

## .env.example additions

```
DISCORD_TOKEN=your-token-here
DISCORD_GUILD_ID=your-server-id-here
```
