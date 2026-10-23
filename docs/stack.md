# Stack

## Backend (`backend/pyproject.toml`)

| Tech | Version | Why |
|---|---|---|
| Python | 3.13 | |
| FastAPI | ≥0.135 | async, OpenAPI → generated frontend types |
| SQLModel | ≥0.0.38 | one model for DB and schema |
| fastapi-users | ≥15.0.5 | cookie JWT login, users routes |
| Alembic | ≥1.13 | migrations (single baseline since the CSV rebuild) |
| asyncpg + psycopg | | asyncpg at runtime, psycopg for Alembic |
| slowapi | ≥0.1.9 | rate limiting (one limiter in `app/core/rate_limit.py`) |
| sqladmin | ≥0.27 | `/admin` (read-only views) |
| PostgreSQL | 16 | naive-UTC timestamps |
| uv, ruff, pytest(-asyncio) | | package manager, lint/format, tests on a real Postgres |

## Frontend (`frontend/package.json`)

| Tech | Version | Why |
|---|---|---|
| SvelteKit | ^2.70.3 | runes; adapter-node for prod |
| Svelte | ^5.55 | |
| Vite | ^8 | |
| TypeScript | ~5.6 | strict |
| Tailwind CSS 4 + DaisyUI 5 | | theme `night` |
| ECharts | ^6.1 | used directly (no wrapper), SVG renderer |
| vitest 4 + Testing Library | | unit/component tests |
| Playwright | ^1.64 | e2e in `frontend/e2e/` |
| openapi-typescript | via npx | generates `src/lib/core/api.d.ts` |

SvelteKit 3 is not adopted yet. It removes `$lib` (use `#lib`), moves `svelte.config.js` into the Vite plugin and changes `$env`. That migration is a roadmap item.

## Infra

| Tech | Role |
|---|---|
| Podman compose | local dev/prod/e2e via the Makefile (`docker compose` in GitHub CI) |
| Caddy 2 | TLS, security headers, `/api/*` and `/admin*` → backend, rest → frontend |
| dev compose | db, backend (`--reload`), frontend (`npm run dev`) |
| prod compose | db, backend (2 workers), frontend (node build), caddy |
| e2e compose | db-e2e :5433, backend-e2e :8001, frontend-e2e :5174 |

## Rejected

- **Automatic upload** (watcher, collector, API token): the user uploads CSVs by hand.
- **Discord bot, JSONL ingest, `pricetracker*` addons:** removed in the ArcheMarket rebuild.
- **External store library:** Svelte 5 runes are enough.
- **SQLite or DB mocks in tests:** tests use a real Postgres. Mocks once hid a production migration bug.
- **Dual-axis charts:** two measures go in two panels.
