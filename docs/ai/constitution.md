# Constitution

Rules that do not change without a deliberate decision. When you change one, record why.

## API

- All endpoints live under `/api/`; the admin is at `/admin`, not under `/api`.
- Only a superuser can import market files through `POST /api/import`. Any signed-in active user can import their own `inventory.csv`. Market reads are public.
- Inventory data is per user. Every inventory query filters by the signed-in user, and another user's character is 404.
- Production has no password login: Google sign-in only. Google sign-in never creates accounts; they come only from `create-superuser`.
- The import is idempotent: the same file uploaded twice changes nothing.
- Newest scan wins per (item, date). An older scan never overwrites newer data.
- Every data line of an upload is accounted for: `inserted + updated + skipped + error_count == rows`.

## Database

- Naive UTC everywhere. Never store timezone-aware datetimes.
- Copper is stored as integers, with `bigint` for prices and volume.
- An item's natural key is `(item_type, item_grade)`. Its name is unique while only single-grade items are tracked.
- A schema change needs an Alembic migration, and `alembic check` must stay clean.

## Code

- One rate limiter singleton, in `app/core/rate_limit.py`.
- Import `formatCurrency` from the shared lib; never redefine it.
- Modules talk to each other through services, not through each other's models.
- Every module has the same core file set. Any extra file states its reason in its first line.
- Frozen code (`*/frozen/`) is not imported or edited outside a planned rebuild.

## Tests

- Tests use a real PostgreSQL (`app_test`), with no DB mocks.
- Test data is unique: the DB is not cleaned between tests.
- No real character names in fixtures or docs: use made-up names (`Alpha`, `Bravo`).
- Game icons are never committed; they live in the icon cache volume.
- Tests mirror the code layout.

## Git & workflow

- Never commit directly to `main`. Never push or merge without an explicit request.
- Commit format: `type(scope): description` (feat, fix, chore, docs, refactor, test, ci).
- Non-trivial change: design, then plan, then implementation, with approval in between.

## Infra

- Podman compose locally, docker compose in CI, same compose files.
- Caddy terminates TLS and proxies traffic.
- Dev runs 3 services (db, backend `--reload`, frontend dev). Prod runs 4 (db, backend with 2 workers, frontend node, caddy).
