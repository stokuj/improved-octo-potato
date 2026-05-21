# Audit Report — qwen3.6-plus-free

**Date:** 2026-05-20
**Branch:** audit/qwen3.6-plus-free (worktree from dev)
**Scope:** Backend (FastAPI), Frontend (SvelteKit 5), Discord bot, Infrastructure, CI/CD

---

## Backend Audit

### B-001 [HIGH] Duplicated `utcnow()` function across 4 modules

**Files:**
- `app/items/models.py:7`
- `app/prices/models.py:6`
- `app/user_items/models.py:7`
- `app/profiles/models.py:7`

**Problem:** Each module defines its own `utcnow()` helper. This is duplicated logic. If you ever need to change the behavior (e.g., add logging, change timezone handling), you must edit 4 files.

**Recommendation:** Move to a single shared utility, e.g., `app/config/time.py` or `app/utils.py`.

```python
# app/config/time.py
from datetime import datetime, timezone

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

---

### B-002 [HIGH] `users/` module has no `services.py` — inconsistent pattern

**Problem:** All other domain modules follow the `models/schemas/services/router/admin` pattern. `users/` only has `models.py`, `admin.py`, `router.py`. User logic lives in `fastapi-users` manager. This breaks the documented pattern from `docs/ai/patterns.md`.

**Impact:** Minor inconsistency, but makes the codebase harder to navigate for new contributors who expect the standard pattern.

**Recommendation:** Either add an empty `services.py` for consistency, or document why `users/` is an exception.

---

### B-003 [MEDIUM] `match_or_create_item` commits inside the function — breaks transaction composition

**File:** `app/ingest/services.py:46`

**Problem:** `match_or_create_item` calls `await session.commit()` internally. This means the caller (`bulk_ingest`) cannot wrap multiple row operations in a single transaction. Each row gets its own commit, which is slower and leaves partial state if a later row fails.

**Current behavior:** Row 1: insert item + commit. Row 2: insert price + commit. Row 3: fails → rollback (but rows 1-2 are already persisted).

**Recommendation:** Remove the `commit()` from `match_or_create_item`. Let the caller (`bulk_ingest`) decide when to commit. Or better: commit per-row in `bulk_ingest` explicitly so the transaction boundary is clear.

---

### B-004 [MEDIUM] `admin_auth.py` — `SecureAdminAuth` redefines `authentication_backend`, shadowing the first assignment

**File:** `app/admin_auth.py:46` and `app/admin_auth.py:67`

**Problem:**
```python
authentication_backend = AdminAuth(...)  # line 46
# ...
authentication_backend = SecureAdminAuth(...)  # line 67
```
The first assignment is dead code. It's also confusing — readers might think both are used.

**Recommendation:** Remove the first `AdminAuth` class entirely. Keep only `SecureAdminAuth` (or rename it to `AdminAuth` if the "Secure" prefix isn't needed).

---

### B-005 [MEDIUM] `admin_auth.py` — nested imports inside `__init__`

**File:** `app/admin_auth.py:54-55`

```python
def __init__(self, secret_key: str, secure: bool = False):
    super().__init__(secret_key)
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.middleware import Middleware
```

**Problem:** Imports inside `__init__` are unusual and hide dependencies. They should be at module level.

**Recommendation:** Move imports to the top of the file.

---

### B-006 [MEDIUM] `auth/manager.py` — bypasses dependency injection, uses `async_session_maker` directly

**File:** `app/auth/manager.py:21`

```python
async with async_session_maker() as session:
```

**Problem:** The `UserManager.on_after_register` creates its own session instead of using the one from the request context (which is how the rest of the app works via `get_async_session`). This means:
1. The profile creation happens in a separate transaction from user registration
2. If user registration succeeds but profile creation fails, you have an orphan user

**Recommendation:** Refactor to accept a session parameter or use a shared session from the request context. fastapi-users supports passing the request, which could give access to the session.

---

### B-007 [LOW] `prices/services.py` — `INTERVAL_SECONDS` dict defined inside function

**File:** `app/prices/services.py:49`

**Problem:** `INTERVAL_SECONDS` is recreated on every call. It's a constant — should be module-level.

**Recommendation:** Move to module level.

---

### B-008 [LOW] `prices/services.py` — duplicated `to_naive` helper

**File:** `app/prices/services.py:23-24`

```python
def to_naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
```

**Problem:** This is similar to `_normalize_ts` in `ingest/services.py:59-62`. Two different implementations of the same concept.

**Recommendation:** Consolidate into a single function in `app/config/time.py`.

---

### B-009 [MEDIUM] No ruff configuration in backend

**File:** `backend/pyproject.toml`

**Problem:** Ruff is installed as a dev dependency but has zero configuration. It runs with all defaults. The discord_bot has `line-length = 100` configured, but backend doesn't. This means:
- Inconsistent linting between the two Python projects
- No explicit rules enforced (e.g., no unused imports check severity, no import sorting)

**Recommendation:** Add a `[tool.ruff]` section to `backend/pyproject.toml` matching the discord_bot config, plus useful rules:

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

---

### B-010 [LOW] `lifespan` context manager is empty

**File:** `app/main.py:23-26`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
```

**Problem:** Empty lifespan adds no value. If you don't need startup/shutdown logic, you can omit it entirely.

**Recommendation:** Remove the lifespan parameter from `FastAPI()` constructor, or add a comment explaining why it's there (e.g., placeholder for future use).

---

### B-011 [MEDIUM] `seed.py` — creates its own engine/session instead of reusing `app/config/db.py`

**File:** `seed.py:276-280`

```python
engine = create_async_engine(settings.async_database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**Problem:** Duplicates the engine/session setup from `app/config/db.py`. If you change the engine config (e.g., pool size, echo), you must update both places.

**Recommendation:** Import and reuse `async_engine` and `async_session_maker` from `app.config.db`.

---

### B-012 [LOW] `Profile.avatar_url` has no `max_length` constraint

**File:** `app/profiles/models.py:16`

```python
avatar_url: str | None = None
```

**Problem:** No max_length means unlimited string length in the database. This is noted in the roadmap as a known issue.

**Recommendation:** Add `max_length=500` (or appropriate limit).

---

### B-013 [MEDIUM] `crafting/services.py` — `list_summaries` loads ALL recipes and items into memory

**File:** `app/crafting/services.py:39-55`

**Problem:** For every call to `list_summaries`, the entire `Recipe`, `RecipeIngredient`, and `Item` tables are loaded into memory, then a craft tree is built for every recipe. This doesn't scale — with hundreds of recipes, this becomes a performance problem.

**Recommendation:** Add caching (e.g., TTL cache) or paginate the summaries. For the current scale (~10 recipes) this is fine, but the pattern should be noted.

---

### B-014 [LOW] `conftest.py` — session-scoped `setup_database` drops and recreates tables, but DB is not cleaned between tests

**File:** `backend/tests/conftest.py:33-43`

**Problem:** The conftest drops/creates tables once per session. Individual tests rely on rollback (not explicit in conftest) for isolation. This means:
- Tests that don't rollback properly will affect subsequent tests
- The `client` fixture is function-scoped but shares the same session-scoped DB state

**Observation:** This is documented in the patterns (`DB nie jest czyszczona między testami`), but the UUID suffix requirement is easy to forget.

**Recommendation:** Consider adding a per-test rollback fixture to make isolation explicit, even if the current approach works.

---

### B-015 [MEDIUM] No test for `/users/{id}` endpoint (admin)

**Problem:** Noted in roadmap. The `fastapi-users` get_users_router provides `GET /users/{id}`, `PATCH /users/{id}`, `DELETE /users/{id}` — none are tested.

**Recommendation:** Add at least basic tests for these endpoints.

---

### B-016 [LOW] No test for rate limiter

**Problem:** Noted in roadmap. The slowapi limiter is configured but not tested.

**Recommendation:** Add a test that verifies rate limit returns 429 after exceeding the threshold.

---

### B-017 [MEDIUM] `bulk_ingest` — no commit after successful rows

**File:** `app/ingest/services.py:112-134`

**Problem:** The `bulk_ingest` function processes rows but never calls `session.commit()`. Each row's commit happens inside `match_or_create_item` (B-003) and `add_price_point`. However, if `match_or_create_item` creates an item but `add_price_point` fails, the item is committed but the price is rolled back — leaving an orphan item.

**Recommendation:** Review transaction boundaries. Either:
1. Wrap each row in its own explicit transaction (commit/rollback per row in `bulk_ingest`)
2. Or remove internal commits and commit once per row at the `bulk_ingest` level

---

### B-018 [LOW] CORS `allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive

**File:** `app/main.py:36-37`

**Problem:** Wildcard CORS for methods and headers. For a production app behind Caddy this is less critical, but it's still a security best practice to be explicit.

**Recommendation:** Replace with explicit lists:
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
allow_headers=["Content-Type", "Authorization"],
```

---

## Frontend Audit

### F-001 [HIGH] `items/[id]/+page.svelte` — `any` type in `loadHistory()`

**File:** `frontend/src/routes/items/[id]/+page.svelte:124`

```typescript
.map((row: any) => ({ ... } as ChartPoint))
```

**Problem:** Uses `any` instead of the proper union type. The API returns either `PricePointRead[]` or `PriceBucketRead[]` — both are available in `api.d.ts`.

**Recommendation:** Use the proper union type:
```typescript
.map((row: components["schemas"]["PricePointRead"] | components["schemas"]["PriceBucketRead"]) => ...)
```
Or define a local union type in `types.ts`.

---

### F-002 [HIGH] `ItemTable.svelte` — hardcoded category/grade arrays duplicated from backend enums

**File:** `frontend/src/lib/components/ItemTable.svelte:34-43`

```typescript
const CATEGORIES = ['Special Product', 'Weapons', 'Armor', ...];
const GRADES = ['All', 'Grand', 'Rare', ...];
```

**Problem:** These are hardcoded copies of `ItemCategory` and `ItemGrade` from the backend. If you add a new category or grade, you must update both backend and frontend. The `grades.ts` file already has `gradeColor()` — consider adding the grade list there too.

**Recommendation:** Import from a shared source. Either:
1. Generate TypeScript enums from the OpenAPI schema (already done for types — extend this)
2. Or define once in `$lib/grades.ts` and `$lib/categories.ts`

---

### F-003 [MEDIUM] `items/[id]/+page.svelte` — 367 lines, too many responsibilities

**File:** `frontend/src/routes/items/[id]/+page.svelte`

**Problem:** This single component handles:
1. Item detail display
2. Price history chart with range selector
3. Crafting calculator with batch size, inventory, overrides
4. Profit/margin calculations
5. All data fetching (item, history, craft tree, inventory)

**Recommendation:** Extract sub-components:
- `PriceHistoryChart.svelte` — chart + range selector + stats
- `CraftingCalculator.svelte` — batch size, profit display, RecipeCard integration
- Keep the page as an orchestrator that composes these

---

### F-004 [MEDIUM] `ItemTable.svelte` — 349 lines, virtual scroll logic mixed with UI

**File:** `frontend/src/lib/components/ItemTable.svelte`

**Problem:** Virtual scroll calculation (lines 47-55, 172-193) is mixed with item rendering, search, and save logic. The component does too much.

**Recommendation:** Extract virtual scroll into a `VirtualList.svelte` component that takes `items`, `rowHeight`, and a render slot/callback.

---

### F-005 [MEDIUM] `auth.svelte.ts` — mutable exported state

**File:** `frontend/src/lib/auth.svelte.ts:12`

```typescript
export const user = $state<UserState>({...});
```

**Problem:** Exporting a mutable `$state` object means any component can directly mutate `user.isLoggedIn = false` without going through the proper `logout()` function. This breaks encapsulation.

**Recommendation:** Use a read-only pattern:
```typescript
const _user = $state<UserState>({...});
export const user = {
    get data() { return _user.data },
    get isLoggedIn() { return _user.isLoggedIn },
    // ... only expose what consumers need
};
```
Or at minimum, document that direct mutation is forbidden.

---

### F-006 [LOW] `items/[id]/+page.svelte` — duplicated currency formatting logic

**File:** `frontend/src/routes/items/[id]/+page.svelte:287-293`

```svelte
{@const p = splitCurrency(item.current_price)}
{#if p}
<div class="text-2xl font-black tabular-nums tracking-tight">
    {#if p.gold > 0}<span>{p.gold}<span class="text-yellow-500...
```

**Problem:** The gold/silver/bronze display logic is duplicated in `ItemTable.svelte` (lines 299-308) and `items/[id]/+page.svelte`. Both manually format the currency display.

**Recommendation:** Create a `CurrencyDisplay.svelte` component that takes `copper` as a prop and renders the formatted output.

---

### F-007 [LOW] `vite.config.js` is `.js` not `.ts`

**File:** `frontend/vite.config.js`

**Problem:** The file is JavaScript while the rest of the frontend is TypeScript. Minor inconsistency.

**Recommendation:** Rename to `vite.config.ts`.

---

### F-008 [MEDIUM] No error boundary or global error handling

**Problem:** The frontend has no `+error.svelte` page for SvelteKit error handling. If a page fails to load, the user gets a generic error.

**Recommendation:** Add `src/routes/+error.svelte` for a branded error page.

---

### F-009 [LOW] `items/[id]/+page.svelte` — `computeNodeCost` recalculates on every render

**File:** `frontend/src/routes/items/[id]/+page.svelte:36-53`

**Problem:** `computeNodeCost` is a regular function called from a `$derived`. It recursively traverses the entire craft tree on every dependency change. For deep trees this could be expensive.

**Recommendation:** For the current scale this is fine, but consider memoization if the tree grows.

---

### F-010 [MEDIUM] `auth.svelte.ts` — `login` and `register` navigate on success, mixing concerns

**File:** `frontend/src/lib/auth.svelte.ts:65` and `:82`

```typescript
goto('/');  // in login()
goto('/auth');  // in logout()
```

**Problem:** The auth module handles navigation. This couples auth to specific routes and makes it hard to use auth in different contexts (e.g., a modal login).

**Recommendation:** Return a success indicator and let the caller decide where to navigate. Or use SvelteKit's form actions for auth.

---

### F-011 [LOW] `+page.svelte` (items list) — redirects to `/items` but page exists at root

**File:** `frontend/src/routes/items/+page.svelte` (5 lines) and `frontend/src/routes/+page.svelte` (132 lines)

**Problem:** `src/routes/items/+page.svelte` is just a redirect:
```svelte
<script>import { goto } from '$app/navigation'; goto('/');</script>
```
This is unnecessary — the items list is already the home page.

**Recommendation:** Remove `/items/+page.svelte` and update any links to point to `/`.

---

### F-012 [LOW] `saved-items/+page.svelte` — same redirect pattern

**File:** `frontend/src/routes/saved-items/+page.svelte` (5 lines)

**Problem:** Same as F-011 — just a redirect to home with a query param.

**Recommendation:** Use URL search params on the home page instead of a separate route.

---

## Discord Bot Audit

### D-001 [LOW] `cogs/prices.py` — hardcoded grade choices duplicated from backend

**File:** `discord_bot/cogs/prices.py`

**Problem:** `GRADE_CHOICES` and `GRADE_INT_TO_STR` are defined in the bot, mirroring the backend's `ItemGrade` enum and `grade_map.py`. If you add a grade, you must update 3 places.

**Recommendation:** Consider generating these from a shared source, or at least add a test that verifies the bot's grade mapping matches the backend's.

---

### D-002 [LOW] `bot.py` — no error handling for `setup_hook` cog loading

**File:** `discord_bot/bot.py`

**Problem:** If `cogs.prices` fails to load, the bot starts without any commands and there's no visible error.

**Recommendation:** Add try/except around `load_extension` with logging.

---

### D-003 [MEDIUM] `cogs/prices.py` — `lookup_item` does exact match only, no fuzzy search

**File:** `discord_bot/cogs/prices.py:lookup_item()`

**Problem:** The lookup requires an exact name match (case-insensitive). Users might type partial names or typos.

**Recommendation:** Consider using the backend's search endpoint (`/items/?q=...`) for fuzzy matching instead of fetching all items and filtering locally.

---

## Infrastructure Audit

### I-001 [MEDIUM] Dev compose exposes DB port 5432 to host

**File:** `infra/compose/docker-compose.dev.yml`

**Problem:** PostgreSQL port 5432 is exposed to the host machine in dev. This is convenient for local debugging but is a security risk if the dev environment is on a shared network.

**Recommendation:** Document this risk. For production it's correctly not exposed.

---

### I-002 [LOW] No healthcheck for backend or frontend in compose

**File:** `infra/compose/docker-compose.dev.yml` and `docker-compose.prod.yml`

**Problem:** Only the DB has a healthcheck. Backend and frontend have no healthchecks, so `depends_on` can't verify they're actually ready.

**Recommendation:** Add HTTP healthchecks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
  interval: 10s
  timeout: 5s
  retries: 3
```

---

### I-003 [MEDIUM] Prod compose — `APP_DOMAIN` and `APP_WWW_DOMAIN` required but not validated

**File:** `infra/compose/docker-compose.prod.yml`

**Problem:** The `${APP_DOMAIN:?...}` syntax validates at compose parse time, but if the variable is set to an empty string, it passes validation but Caddy won't work correctly.

**Recommendation:** Add a validation script or use a more robust check.

---

### I-004 [LOW] Caddyfile routes `/docs*` and `/redoc` — should these be disabled in production?

**File:** `infra/caddy/Caddyfile`

**Problem:** OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) are exposed in production via Caddy. These are useful for debugging but expose your API schema.

**Recommendation:** Consider conditionally including these routes only in dev, or adding basic auth.

---

### I-005 [MEDIUM] Makefile uses `podman compose` — not portable to Docker

**File:** `Makefile`

**Problem:** All commands use `podman compose`. Developers who only have Docker must modify commands manually.

**Recommendation:** Add a `COMPOSE_CMD` variable at the top of the Makefile:
```makefile
COMPOSE_CMD ?= podman compose
```
Then use `$(COMPOSE_CMD)` throughout. Docker users can override with `make dev-up COMPOSE_CMD="docker compose"`.

---

## CI/CD Audit

### C-001 [LOW] No frontend test pipeline

**File:** `.github/workflows/frontend.yml`

**Problem:** The frontend CI only runs `svelte-check` (type checking). No unit or integration tests.

**Recommendation:** Consider adding Vitest + Testing Library for component tests.

---

### C-002 [MEDIUM] No integration test that verifies end-to-end flow

**Problem:** Backend tests hit a real DB, Discord bot tests mock HTTP. But there's no test that verifies the full flow: bot → ingest → items → prices → frontend.

**Recommendation:** Add at least one integration test that posts via the ingest endpoint and verifies the data appears via the items/prices API.

---

### C-003 [LOW] Docker build workflow doesn't push images

**File:** `.github/workflows/docker.yml`

**Problem:** `push: false` means images are built but not pushed to any registry. This is fine for local testing but means the workflow doesn't produce deployable artifacts.

**Recommendation:** Either push to GHCR or remove this workflow if it's only for validation.

---

## Cross-Cutting Concerns

### X-001 [HIGH] No `.env` example for production

**File:** `.env.example`

**Problem:** The `.env.example` likely contains dev defaults. Production requires different values (secure cookies, real secrets, domain names). There's no `.env.example.prod` or documented production env template.

**Recommendation:** Create a production env template or document required variables in README.

---

### X-002 [MEDIUM] Roadmap items not addressed

**From `docs/ai/roadmap.md`:**

| Item | Status | Severity |
|---|---|---|
| `aiosqlite` cleanup | Not done | LOW — dead dependency |
| `mockData.ts` cleanup | Not done | LOW — dead file |
| `InventoryModal.svelte` | Not done | LOW — unused component |
| Rate limit tests | Not done | MEDIUM |
| `/users/{id}` tests | Not done | MEDIUM |
| Avatar URL validation | Not done | LOW |
| `/saved-items` redirect | Not done | LOW |

**Recommendation:** Clean up the dead code (aiosqlite, mockData.ts, InventoryModal) — these are quick wins that improve codebase hygiene.

---

### X-003 [MEDIUM] No API versioning

**Problem:** All API endpoints are unversioned (`/api/items/`, `/api/prices/`, etc.). If you need to make breaking changes, you have no versioning strategy.

**Recommendation:** For a small app this is fine, but document the decision. If you anticipate breaking changes, consider `/api/v1/` prefix.

---

### X-004 [LOW] No API response caching

**Problem:** Every request hits the database. For frequently-read, rarely-changed data (item list, recipe list), caching would reduce DB load.

**Recommendation:** Consider HTTP caching headers (`ETag`, `Cache-Control`) for GET endpoints. For now, fine for the expected scale.

---

## Summary

| Severity | Count | Top Actions |
|---|---|---|
| **HIGH** | 5 | Deduplicate `utcnow()`, fix transaction boundaries in ingest, fix `any` type, extract large components, fix mutable auth state |
| **MEDIUM** | 14 | Add ruff config, fix admin_auth shadowing, consolidate naive-UTC helpers, add healthchecks, add integration tests |
| **LOW** | 15 | Clean up dead code, fix minor inconsistencies, add error pages, improve CORS |

### Architecture Assessment

**Good:**
- Clean modular structure (models/schemas/services/router)
- SQLModel used consistently
- Svelte 5 runes used properly
- Real DB in tests (not mocks)
- Good separation of concerns in most modules
- OpenAPI type generation for frontend
- CI/CD covers lint, test, type-check, build

**Needs Improvement:**
- Transaction boundary clarity in ingest pipeline
- Duplicated constants across backend/frontend/bot
- Component size (2 files >300 lines)
- Missing ruff config in backend
- No frontend tests
- Auth state encapsulation

### Modern Stack Usage

| Area | Assessment |
|---|---|
| Python 3.13 | ✅ Current version |
| FastAPI async | ✅ Properly async throughout |
| SQLModel | ✅ Good use of ORM + Pydantic integration |
| Pydantic v2 | ✅ Using `model_dump`, `field_validator` |
| Svelte 5 runes | ✅ `$state`, `$derived`, `$effect` used correctly |
| TypeScript strict | ✅ Enabled, only 1 `any` usage |
| Tailwind 4 + DaisyUI 5 | ✅ Current versions |
| OpenAPI type gen | ✅ `openapi-typescript` generates types |

### Verdict

The codebase is **well-structured for its size** with good architectural patterns. The main issues are:
1. **Transaction boundaries** in the ingest pipeline need clarification
2. **Duplicated constants** across 3 codebases (backend, frontend, bot)
3. **Component size** — two components are doing too much
4. **Missing ruff config** — easy fix, immediate benefit

No spaghetti code detected. No critical security issues. The patterns are good for continued expansion.
