# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A game marketplace/price tracker web app (MMO) where users browse items by category and grade, track price history, and save items to a personal watchlist.

## Stack

- **Backend**: FastAPI + SQLModel + PostgreSQL, managed with `uv`, Python 3.13+
- **Frontend**: SvelteKit 5 + Tailwind CSS v4 + DaisyUI + ECharts
- **Auth**: `fastapi-users` with JWT stored in HTTP-only cookies (cookie name: `fastapiusersauth`)
- **Admin**: `sqladmin` panel at `/admin`, accessible only to superusers
- **Migrations**: Alembic (sync engine for migrations, async engine for the app)
- **Dev/Prod**: `podman compose` — all services in Docker including frontend with bind-mount hot reload

## Commands

### Backend (run from `backend/` — local dev without Docker)

```bash
uv run fastapi dev app/main.py          # http://localhost:8000
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "<message>"
```

### Tests (run from `backend/`)

```bash
uv run pytest                           # full suite
uv run pytest tests/test_auth.py -v    # single file
uv run pytest -k "test_login" -v       # single test
```

**Test prerequisites:** PostgreSQL running with an `app_test` database:
```bash
podman compose -f infra/compose/docker-compose.dev.yml up db -d
podman exec $(podman ps -q --filter name=db) psql -U postgres -c "CREATE DATABASE app_test;" 2>/dev/null || true
```

Tests set their own env vars in `tests/conftest.py` — no `.env` needed.

### Docker / Makefile (from repo root)

```bash
make dev-up        # start db + backend + frontend (all in Docker, bind mounts)
make dev-down
make dev-logs
make dev-status
make prod-up       # full stack with Caddy (TLS)
make prod-down
make test          # bring up test db and run pytest
make migrate       # alembic upgrade head inside dev backend container
make seed          # seed db with 24 sample items + 30 days price history
```

**Dev setup:**
```bash
cp .env.example .env
make dev-up
```

**Prod setup:**
```bash
cp .env.example .env   # set APP_DOMAIN, APP_WWW_DOMAIN, strong secrets
make prod-up
```

## Infrastructure Layout

```
infra/
  compose/
    docker-compose.dev.yml   # db + backend + frontend (bind mounts, hot reload)
    docker-compose.prod.yml  # db + backend + frontend + Caddy
  caddy/
    Caddyfile                # /api/* /admin* /redoc /docs* → backend; rest → frontend
Makefile                     # shortcuts using podman compose
```

**Bind mount note (Fedora / rootless podman):** All bind mounts in dev compose use `:z` suffix for SELinux relabeling — without it the container cannot read host files.

**Frontend container:** Uses `node:22-alpine` with `../../frontend:/app:z` bind mount and a named volume `frontend_node_modules` at `/app/node_modules` to isolate from host packages. Vite started with `--host` so port 5173 is accessible.

**Backend Dockerfile:** Based on `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` (avoids Docker Hub auth issues). Uses `uv sync --frozen --no-cache --no-dev`. Commands in compose override CMD with `uv run alembic upgrade head && uv run uvicorn ...`.

## Environment Variables

Root `.env.example` covers all services. Key variables:
- `DATABASE_URL` — sync psycopg URL (Alembic)
- `ASYNC_DATABASE_URL` — asyncpg URL (FastAPI runtime)
- `AUTH_SECRET` / `ADMIN_SESSION_SECRET` — must be ≥32 chars; validated at startup
- `CORS_ORIGINS` — JSON array string e.g. `'["http://localhost:5173"]'`; defaults to localhost:5173
- `APP_DOMAIN` / `APP_WWW_DOMAIN` — required for prod (Caddy TLS + CORS)
- `COOKIE_SECURE` — set to `"true"` in prod compose automatically

## Architecture

### Backend module layout

Each domain (`items`, `prices`, `profiles`, `user_items`, `users`, `auth`) is a self-contained package with `models.py`, `schemas.py`, `services.py`, `router.py`, and optionally `admin.py`.

- `app/config/db.py` — `get_async_session` dependency; sync + async engines
- `app/config/settings.py` — `Settings` via pydantic-settings; `cors_origins` parsed from JSON array env var
- `app/main.py` — all API routers wrapped in `APIRouter(prefix="/api")`; admin at `/admin` (sqladmin, not under `/api`)
- `app/auth/backend.py` — JWT cookie transport, 1-hour TTL; login returns **204** not 200
- `app/auth/manager.py` — auto-creates `Profile` (private by default) on registration

### API routing

All API endpoints live under `/api/` (e.g. `/api/items/`, `/api/auth/login`). The admin panel is at `/admin`, API docs at `/docs` and `/redoc` — none of these go through the `/api` prefix.

### Database schema

```
User (UUID PK)
 ├── Profile (1-to-1, auto-created on register)
 └── UserItem (many-to-many join to Item, unique on user_id+item_id)

Item (int PK)
 └── PricePoint (many per item; source + captured_at)
```

`Item.current_price` is a denormalized snapshot updated atomically by `POST /api/items/{id}/prices`. Full history lives in `PricePoint`.

### Datetime handling

All `TIMESTAMP WITHOUT TIME ZONE` columns use **naive UTC**. The `utcnow()` helper in each model returns `datetime.now(timezone.utc).replace(tzinfo=None)`. Strip tzinfo from external input before writing — see `prices/services.py:add_price_point`.

### Frontend

- Global auth state: Svelte 5 `$state` in `src/lib/auth.svelte.js`; `checkMe()` called in `+layout.svelte`
- API base URL: `PUBLIC_API_URL` env var, fallback `http://localhost:8000/api` (`src/lib/config.js`)
- All API calls use `credentials: 'include'` for the JWT cookie
- Routes: `/` (home, top 3 items), `/auth`, `/items`, `/items/[id]` (detail + ECharts price chart), `/saved-items`, `/settings`, `/about`

### Migrations

Always import all models in `alembic/env.py` before autogenerate — the file already has them. Sync and async engines must use matching URLs.

## Adding a New Domain Module

1. Create `app/<domain>/` with `models.py`, `schemas.py`, `services.py`, `router.py`
2. Import the model in `alembic/env.py`
3. Register the router in `app/main.py` (inside the `api` APIRouter)
4. Optionally add `ModelAdmin` in `<domain>/admin.py` and register in `app/admin.py`

## Test Infrastructure

`pytest-asyncio` in `asyncio_mode = "auto"` with session-scoped event loop. `conftest.py` sets `os.environ` before any app imports (pydantic-settings reads at import time). Each test file that needs direct DB access creates its own engine with `NullPool`.

- `follow_item` (`POST /api/user-items/{id}`) is idempotent: 201 on first follow, 204 if already followed
- Use UUID-based unique data per test to avoid cross-test conflicts
- Fresh engine in verify steps (not the fixture session) to avoid stale transaction snapshots
