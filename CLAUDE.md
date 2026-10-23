# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ArcheRage Market Tracker. The user exports AH data with the ArcheMarket game addon (a separate repo) as `listings.csv` and `market.csv`, and their bag and warehouse (`inventory.csv`) and house chests (`chests.csv`) with the ArcheBag addon, and uploads them by hand on `/import`. The app stores them idempotently and shows:
- `/market`: a 14-day chart, the cheapest current offers, and a today-vs-7-days table;
- `/items`: each character's bag, warehouse and bag chests, and the house chests, as game-like tile grids.

Stack: FastAPI + SQLModel + PostgreSQL 16, SvelteKit 2 (Svelte 5 runes) + DaisyUI + ECharts, podman compose.

Deeper docs: `docs/architecture.md` (schema, import flow, invariants), `docs/patterns.md` (conventions and gotchas), `docs/constitution.md` (rules).

## Commands

```bash
# Backend (from backend/)
uv run pytest                                   # needs Postgres with db app_test on localhost:5432
TEST_PG_HOSTPORT=localhost:5434 uv run pytest   # point tests at another Postgres
uv run pytest tests/market/test_import.py::test_sample_first_and_second_upload -v
uv run ruff check . && uv run ruff format --check .
uv run alembic revision --autogenerate -m "<msg>"   # then: alembic upgrade head && alembic check
uv run python -m app.auth.cli create-superuser EMAIL PASSWORD   # create admin / reset password

# Frontend (from frontend/)
npm run check                 # svelte-kit sync + svelte-check
npm test                      # vitest (src/** only)
npx vitest run src/lib/market/chart.test.ts
npm run test:e2e              # Playwright, needs the e2e stack (below)

# Regenerate API types without a running server
cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > /tmp/openapi.json
cd ../frontend && npx openapi-typescript /tmp/openapi.json -o src/lib/core/api.d.ts

# Compose (from repo root; uses podman, adds --env-file infra/.env if it exists)
make dev-up | dev-down | dev-reset | dev-logs   # db + backend :8000 + frontend :5173
make seed                                       # import the sample CSVs from backend/tests/market/fixtures
make create-superuser EMAIL=.. PASSWORD=..
make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test   # stack on :5433/:8001/:5174
```

CI (`.github/workflows`):
- **backend:** ruff, `uv lock --check`, pytest, `alembic upgrade head` + `alembic check`.
- **frontend:** svelte-check + vitest.
- **docker:** image builds.
- **infra:** `infra/tests/*.sh`.
- **e2e:** non-blocking Playwright via `docker compose`.

## Architecture

**Backend (`backend/app/`).**
- Domain modules each have the same core files: `models.py`, `schemas.py`, `services.py`, `router.py`, plus `admin.py` where needed. Any other file starts with a one-line reason comment.
- Shared plumbing is in `core/`: settings with prod secret checks, DB, errors, the **single** slowapi `limiter`, and `utcnow`.
- `auth/` holds `User` and fastapi-users with a 7-day cookie JWT. Prod signs in with Google only (existing active superusers, matched by verified email); the password route exists only outside prod. There are no register or reset routes: accounts come only from the CLI. `/admin` reuses the same cookie.
- `market/` holds `Item`, `MarketDay` and `Listing`, plus the market import and read API under `/api/market`.
- `imports/` owns `POST /api/import`. It routes each file by its header: market files are superuser only, and `inventory.csv` and `chests.csv` are open to any active user.
- `inventory/` holds per-user snapshots of places: a character's bag or warehouse, or a chest number. It keeps the two newest per place, keeps each chest's last non-empty name, and exposes the read API and a public Codex icon cache (looked up by `item_type`) under `/api/inventory`.
- `admin/` is sqladmin at `/admin`.
- Every API route is under `/api`. Modules use each other's services, never each other's models.

**Import pipeline** (`market/csv_format.py` then `market/services.py`):
- The file type is detected from the exact header.
- Rows are validated; a bad row becomes `{line, reason}` and the rest still imports.
- Items are resolved in Python by `(item_type, item_grade)`, then by `name`, because Postgres `ON CONFLICT` can target only one of the two unique keys.
- Market days are dated in **Moscow time** (the server clock): `day_date = date(captured_at at UTC+3) − (14 − day)`, with day 14 = today.
- They are deduplicated in memory by `(item_id, day_date)` before an `ON CONFLICT DO UPDATE … WHERE stored.captured_at < new.captured_at`.
- Listings are inserted with `ON CONFLICT DO NOTHING`.
- Each file is one transaction, inserted in chunks of 2 000 rows (asyncpg allows 32 767 bind params).

These invariants must hold:
- re-upload is a no-op;
- the newest scan wins;
- per file, `inserted + updated + skipped + error_count == rows`.

**Frontend (`frontend/src/`).**
- `lib/core/` holds config, auth state (runes + Svelte context), `formatCurrency`, and the generated `api.d.ts` re-exported through `types.ts`.
- `lib/market/` holds the API helpers, `chart.ts` (a pure ECharts option builder: two stacked panels sharing the date axis, no dual-axis), and the components.
- Routes: `/` → `/market`, `/market` (selected item in `?item=`), `/items` (`?character=` and `?chest=`, `All` when missing; `/inventory` redirects here), `/import` (signed in), `/auth` (Google, plus the password form when `PUBLIC_PASSWORD_LOGIN=true`), `/auth/callback`.
- CSP `connect-src` and `img-src` allow the origin of `PUBLIC_API_URL` (`svelte.config.js`), because dev and e2e call the API cross-origin and icons come from the API.
- `lib/inventory/` holds the inventory API helpers, `grid.ts` (tiles, tabs, chest labels, `chestOwner`), `grades.ts` and the tile, grid and `GridPanel` components.

**Frozen code.** `backend/frozen/` and `frontend/frozen/` (crafting) are reference-only, waiting for a rebuild. They are excluded from ruff, pytest, svelte-check, vitest and Docker. Don't import from them or fix them.

## Gotchas

- Tests hit a real Postgres that is **not cleaned between tests**: use unique names and `item_type` values (see `rewrite_fixture` in `tests/market/test_import.py`). Create users with the `make_user` + `login` fixtures, and use `superuser_client` for admin calls. Test emails must use a real TLD like `@example.com`; `EmailStr` rejects `.local`.
- e2e and local dev use the password form (`PUBLIC_PASSWORD_LOGIN=true`, read from `$env/dynamic/public`); no test talks to Google. Backend OAuth tests fake `google_client.get_access_token`/`get_profile`.
- Login is rate-limited to 5/min per IP. Playwright logs in once (`e2e/auth.setup.ts` → storage state), and the rate-limit spec runs last in its own project. A quick local rerun can hit the limit.
- Inventory tests use `backend/tests/inventory/fixtures/inventory.csv` and `chests.csv`. They are anonymised (`Alpha`, `Bravo`); never commit real character names (the ArcheMarket raw files contain one). Tests never call Codex: fake `icons.fetch_codex`, or route its HTTP through `fake_web` (an `httpx.MockTransport`) in `test_icons.py`. `ICON_CACHE_DIR` points to a temp dir.
- Naive UTC datetimes in the DB. Money is integer copper (`bigint`), and `item_grade` is the raw game int.
- Frontend stays on SvelteKit 2: SvelteKit 3 removes `$lib` and `svelte.config.js` (a planned migration). Don't accept dependabot majors for kit, adapter-node or vitest without that migration.
- Schema change: write an Alembic migration (`alembic/script.py.mako` already imports `sqlmodel`); `alembic check` must pass.

## Rules

- Never push, merge, or commit to `main` without an explicit request. Commit format: `type(scope): description`.
- Never modify `.env*` files. `infra/.env.example` is the only template.
- Code comments, docs and PR text are in English; talk to the user in their language.
