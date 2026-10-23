# Code patterns & gotchas

## Backend module layout {#new-domain}

Every domain module in `backend/app/<domain>/` has the same core files:

```
models.py    SQLModel tables
schemas.py   Pydantic request/response models
services.py  async functions taking a session
router.py    APIRouter, calls services
admin.py     sqladmin views (when the module needs them)
```

- **Any other file starts with a one-line comment giving its reason.** Examples: `market/csv_format.py` (pure parsing), and `auth/{backend,manager,dependencies,cli}.py`.
- Shared plumbing lives in `app/core/`, never in a domain module.
- A module never imports another module's models directly, only its services. FKs to other modules' tables are fine.
- Mount new routers in `app/main.py` on the `/api` router. The admin stays at `/admin`.

## Tests mirror the code

- `backend/tests/<module>/test_<subject>.py` mirrors `backend/app/<module>/`. Fixtures live in `tests/market/fixtures/` (the real ArcheMarket samples plus hand-made edge cases).
- The DB is real Postgres (`app_test`) and is shared across tests without cleanup, so use unique data: UUID-suffixed names and random `item_type` offsets (see `rewrite_fixture` in `tests/market/test_import.py`).
- Registration is off. Create users with the `make_user` fixture and log in with the `login` fixture. Use `superuser_client` for admin calls.
- `TEST_PG_HOSTPORT` (default `localhost:5432`) points a local run at another Postgres.
- Frontend unit tests sit next to the code (`*.test.ts`). Route tests live in `src/test/routes/`. Mocks are aliased in `vitest.config.ts`.

## Rate limiter: a single instance

`app/core/rate_limit.py` exports the only `limiter`. Never create a second one.

```python
from app.core.rate_limit import limiter

@router.post("/")
@limiter.limit("10/minute")
async def endpoint(request: Request, ...): ...
```

Login is limited to 5/min per IP. The Playwright suite logs in once (`e2e/auth.setup.ts`, storage state) and runs the rate-limit spec last.

## Auth dependencies

```python
from app.auth.dependencies import current_user, current_superuser
```

## Import idempotency

- Market rows: deduplicate in memory by `(item_id, day_date)` **before** `ON CONFLICT DO UPDATE`. Postgres refuses to update the same row twice in one statement.
- Count inserts and updates with `RETURNING (xmax = 0)`.
- Insert in chunks of at most 2 000 rows: asyncpg allows 32 767 bind params per statement.
- A unique key in Postgres `ON CONFLICT` covers one constraint only. Items have two (type+grade, name), so they are resolved in Python (`resolve_items`).

## Naive UTC in the DB

Store `datetime` values without tzinfo, in UTC (`app.core.time.utcnow`). The game day is computed separately at UTC+3 (`csv_format.GAME_TZ`).

## Frontend

- Import `formatCurrency` from `$lib/core/currency` only.
- Every fetch uses `credentials: 'include'` (cookie JWT). Market fetches go through `$lib/market/api.ts`.
- `src/lib/core/api.d.ts` is generated, so never edit it. Regenerate it without a running server:

  ```bash
  cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > /tmp/openapi.json
  cd ../frontend && npx openapi-typescript /tmp/openapi.json -o src/lib/core/api.d.ts
  ```

  Re-export the types you need from `src/lib/core/types.ts`.
- Keep chart options in pure functions (`lib/market/chart.ts`) so they can be tested without a canvas.

## Frozen code

- `backend/frozen/` and `frontend/frozen/` are reference only.
- Ruff, pytest, svelte-check, vitest and Docker builds ignore them.
- Do not import from them or fix them. They get rebuilt (see the roadmap).

## Podman, not Docker

Locally the Makefile uses `podman compose`, and it passes `--env-file infra/.env` when that file exists. GitHub CI uses `docker compose` with the same files.
