# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Player's PC                          │
│                                                         │
│  ArcheRage Game                                         │
│  └── Lua Addon (pricetracker_folio)                     │
│       └── writes prices.jsonl ──► Watcher daemon        │
│                                        │                │
└────────────────────────────────────────┼────────────────┘
                                         │ HTTP POST /api/ingest/prices
                                         ▼
┌─────────────────────────────────────────────────────────┐
│                      Server                             │
│                                                         │
│  Caddy (TLS termination + reverse proxy)                │
│   ├── /api/*  /admin  /docs  → FastAPI backend          │
│   └── /*                    → SvelteKit frontend        │
│                                                         │
│  FastAPI backend                                        │
│   ├── /api/ingest/prices   (no auth, rate-limited)      │
│   ├── /api/items/          (public read)                │
│   ├── /api/prices/         (authenticated write)        │
│   ├── /api/crafting/       (authenticated)              │
│   ├── /api/user-items/     (authenticated)              │
│   ├── /api/inventory/     (authenticated)              │
│   └── /admin               (superuser only)             │
│                                                         │
│  PostgreSQL                                             │
└─────────────────────────────────────────────────────────┘
                        ▲
                        │ HTTP (slash commands)
              Discord Bot (discord_bot/)
```

## Data Flow: Price Ingestion

1. **Lua addon** hooks `AUCTION_ITEM_SEARCHED` in-game, writes one JSONL row per scan to `prices.jsonl`
2. **Watcher** tails the file from a persisted byte offset, batches rows, POSTs to `/api/ingest/prices`
3. **Ingest endpoint** calls `match_or_create_item` (upsert by name+grade), then `add_price_point`; updates `Item.current_price` atomically; returns partial-success response
4. **Frontend** chart queries `PricePoint` filtered by `source='ah'`

Alternatively, the **Discord bot** (`/addprice`) POSTs directly to `/api/ingest/prices` — same endpoint, same contract.

## Backend Module Boundaries

```
app/
 ├── config/         # db engines, settings, rate_limit singleton
 ├── auth/           # fastapi-users wiring; login returns 204
 ├── users/          # User model + router
 ├── profiles/       # Profile 1-to-1 with User, auto-created on register
 ├── items/          # Item model + CRUD; current_price is denormalized
 ├── prices/         # PricePoint append-only time-series
 ├── user_items/     # watchlist (User ↔ Item many-to-many)
 ├── crafting/       # Recipe + RecipeIngredient; recursive profit calculator
 ├── user_inventory/ # per-user item quantities; upsert (quantity=0 → delete); for-recipe lookup
 ├── ingest/         # public write endpoint; grade_map; partial-success contract
 └── admin/          # sqladmin ModelAdmin registrations
```

Each module is self-contained. Cross-module imports go through services, not directly between models.

## Key Invariants

- **`source='ah'`** must be used consistently by seed, watcher, bot, and frontend chart. `test_consistency.py` enforces this.
- **`Item.current_price`** is always updated in the same transaction as the new `PricePoint` insert — never update one without the other.
- **`slowapi.Limiter`** is a singleton in `app/config/rate_limit.py`. Only one instance must exist; `app.state.limiter` and all `@limiter.limit()` decorators share it.
- **Naive UTC** everywhere in the DB. Never store timezone-aware datetimes; strip `tzinfo` before write.
- **Ingest partial success**: bad rows return 200 with `errors[]`, not 4xx. The watcher advances its offset on any 2xx. Only 429 and 5xx trigger retry with backoff.
- **`session.rollback()`** after a failed `add_price_point` — without it, the SQLAlchemy session stays in a failed-transaction state and poisons subsequent rows in the same batch.
- **`CraftResult.batch_profit`** is total profit for the entire batch (market_price × output_qty × multiplier − total_material_cost), not per single craft.
- **`UserInventory` upsert**: `quantity > 0` uses `ON CONFLICT DO UPDATE` (atomic); `quantity = 0` issues a direct DELETE (also atomic). Never use SELECT-then-delete.

## Frontend State Management

SvelteKit 5 runes (`$state`, `$derived`) — no external store library. Auth state lives in `src/lib/auth.svelte.js` and is checked once in `+layout.svelte`. All fetches use `credentials: 'include'` for the JWT cookie set by the backend.

## Separate Python Projects

Two independent Python projects each with their own `pyproject.toml` and `uv.lock`:

| Directory | Purpose | Key dep |
|---|---|---|
| `backend/` | FastAPI app | fastapi, sqlmodel, fastapi-users, slowapi |
| `discord_bot/` | Slash command bot | discord.py, httpx |

> `watcher/` has been removed. Manual price ingestion goes via Discord bot `/addprice` or direct POST to `/api/ingest/prices`.

Run `uv run ...` from within each project directory. Do not mix their virtual environments.
