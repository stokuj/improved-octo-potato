# Audit Report — ArcheRage Market Tracker

**Date:** 2026-05-20
**Model:** deepseek-v4-pro
**Branch:** deepseek-v4-pro
**Scope:** Full codebase (~100 files across 5 domains)

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 9 |
| High     | 31 |
| Medium   | 39 |
| Low      | 35 |
| **Total** | **114** |

---

## Backend

### SEVERITY: High
**File:** backend/app/items/models.py:7-8 (also prices/models.py:6, profiles/models.py:7, user_items/models.py:7, seed.py:17)
**Problem:** `utcnow()` function duplicated identically in 5 files — DRY violation.
**Recommendation:** Extract to a single shared utility, e.g. `app/utils.py:utcnow()`.

### SEVERITY: High
**File:** backend/app/admin_auth.py:46
**Problem:** `authentication_backend = AdminAuth(...)` at line 46 is immediately overwritten by `authentication_backend = SecureAdminAuth(...)` at line 67 — dead assignment.
**Recommendation:** Remove the dead assignment at line 46.

### SEVERITY: High
**File:** backend/app/main.py:23-25
**Problem:** Empty `lifespan` context manager — does nothing, adds zero setup/teardown logic.
**Recommendation:** Remove the `lifespan` parameter entirely from the FastAPI constructor.

### SEVERITY: High
**File:** backend/app/items/schemas.py:34-36
**Problem:** `ItemFilter` class defined but never imported or used anywhere in the codebase.
**Recommendation:** Delete the class or wire it into the items router as a dependency.

### SEVERITY: High
**File:** backend/app/user_items/schemas.py:8-14
**Problem:** `UserItemRead` class defined but never imported or used anywhere.
**Recommendation:** Delete or use as response_model in user_items router.

### SEVERITY: High
**File:** backend/app/admin.py:12-19
**Problem:** `setup_admin` returns `Admin` but return value is discarded in `main.py:55` — dead return.
**Recommendation:** Remove the return statement from `setup_admin` or capture it in `main.py`.

### SEVERITY: High
**File:** backend/app/profiles/ (models.py)
**Problem:** Profile has a SQLModel table but no `profiles/admin.py` registered in sqladmin panel.
**Recommendation:** Create `profiles/admin.py` with `ProfileAdmin(ModelView, model=Profile)`.

### SEVERITY: High
**File:** backend/app/user_items/ (models.py)
**Problem:** UserItem has a SQLModel table but no `user_items/admin.py` registered in sqladmin panel.
**Recommendation:** Create `user_items/admin.py` and register in `app/admin.py`.

### SEVERITY: High
**File:** backend/app/user_inventory/ (models.py)
**Problem:** UserInventory has a SQLModel table but no `user_inventory/admin.py` registered in sqladmin panel.
**Recommendation:** Create `user_inventory/admin.py` and register in `app/admin.py`.

### SEVERITY: High
**File:** backend/app/admin_auth.py:22
**Problem:** Bare `except Exception:` swallows all authentication errors silently without logging.
**Recommendation:** Add logging (`logger.exception(...)`) before returning False.

### SEVERITY: High
**File:** backend/tests/{test_crafting.py:12, test_ingest.py:16, test_items.py:10, test_prices.py:11, test_user_items.py:11}
**Problem:** `_TEST_URL = os.environ["ASYNC_DATABASE_URL"]` duplicated in 6 test files (also in conftest.py:30).
**Recommendation:** Import `_TEST_URL` from conftest.py or define a pytest fixture for it.

### SEVERITY: High
**File:** backend/tests/{test_auth.py, test_inventory.py, test_prices.py, test_profiles.py, test_user_items.py}
**Problem:** `_email()` helper function duplicated in 5 test files with identical implementation.
**Recommendation:** Move `_email()` to conftest.py as a shared utility.

### SEVERITY: Medium
**File:** backend/app/user_inventory/services.py:8-9
**Problem:** Cross-domain coupling: inventory services imports `build_craft_tree` from `app.crafting.calculator` and `load_all_items`/`load_all_recipes` from `app.crafting.services`.
**Recommendation:** Extract shared recipe tree logic to a neutral utility module or document coupling with a comment.

### SEVERITY: Medium
**File:** backend/app/auth/manager.py:10
**Problem:** Cross-domain coupling: auth domain imports `Profile` from `app.profiles.models` — should be event-driven.
**Recommendation:** Consider emitting an event instead of directly creating a Profile in auth code.

### SEVERITY: Medium
**File:** backend/app/ingest/services.py:16-17
**Problem:** Cross-domain coupling: ingest imports `PricePointCreate` from `app.prices.schemas` and `add_price_point` from `app.prices.services`.
**Recommendation:** Accept as intentional pipeline coupling or create shared price-abstraction layer.

### SEVERITY: Medium
**File:** backend/tests/{test_crafting.py, test_ingest.py, test_items.py, test_prices.py, test_user_items.py}
**Problem:** `db_session` fixture with identical engine/session_maker setup duplicated across 5 test files.
**Recommendation:** Move `db_session` fixture to conftest.py.

### SEVERITY: Medium
**File:** backend/tests/{test_inventory.py, test_prices.py, test_profiles.py, test_user_items.py}
**Problem:** `auth_client` fixture (register + login) duplicated in 4 test files.
**Recommendation:** Move `auth_client` to conftest.py.

### SEVERITY: Medium
**File:** backend/app/ingest/services.py:70
**Problem:** `_collect_item_ids(nodes: list)` has untyped `list` parameter — should be `list[CraftNode]`.
**Recommendation:** Change to `_collect_item_ids(nodes: list[CraftNode]) -> set[int]`.

### SEVERITY: Medium
**File:** backend/app/auth/manager.py:2,19
**Problem:** Uses deprecated `Optional[Request]` pattern — should be `Request | None` (Python 3.13).
**Recommendation:** Replace `Optional[Request]` with `Request | None`.

### SEVERITY: Medium
**File:** backend/app/auth/schemas.py:2,10
**Problem:** `Any` type used for `handler` parameter in `_hide_internal_flags` — overly broad.
**Recommendation:** Use `Callable[..., dict[str, Any]]` for the handler type.

### SEVERITY: Medium
**File:** backend/app/crafting/calculator.py:75
**Problem:** Magic number `10` for maximum recursion depth — should be a named constant.
**Recommendation:** Define `MAX_CRAFT_TREE_DEPTH = 10` at module level.

### SEVERITY: Medium
**File:** backend/app/ingest/services.py:65
**Problem:** Magic number `timedelta(hours=1)` for future timestamp tolerance — hardcoded.
**Recommendation:** Define `FUTURE_TOLERANCE = timedelta(hours=1)` as a module-level constant.

### SEVERITY: Medium
**File:** backend/app/ingest/services.py:88
**Problem:** Broad `except Exception as e` catches all exceptions including KeyboardInterrupt.
**Recommendation:** Catch more specific exceptions (`IntegrityError`, `SQLAlchemyError`).

### SEVERITY: Medium
**File:** backend/app/prices/services.py:23-24
**Problem:** `to_naive()` datetime normalization function duplicates the pattern in `ingest/services.py:59-61` (`_normalize_ts`).
**Recommendation:** Extract shared `to_naive()` to a common utility, e.g. `app/config/db.py`.

### SEVERITY: Medium
**File:** backend/app/ingest/services.py:101-102
**Problem:** `await session.rollback()` only in error path — but `match_or_create_item` (called on line 87) already does its own `session.commit()` inside, potentially splitting the transaction.
**Recommendation:** Review whether both `match_or_create_item` and `add_price_point` should participate in the same transaction.

### SEVERITY: Low
**File:** backend/app/user_items/services.py:76
**Problem:** `type: ignore[arg-type]` comment on `await session.exec(stmt)` — may no longer be needed with newer sqlmodel.
**Recommendation:** Verify if the type ignore is still required with current sqlmodel version.

### SEVERITY: Low
**File:** backend/app/profiles/services.py:16
**Problem:** `type: ignore[arg-type]` comment on `await session.exec(stmt)` — same pattern.
**Recommendation:** Verify if still needed.

### SEVERITY: Low
**File:** backend/alembic/versions/*.py (5 files)
**Problem:** Old-style `Union[str, Sequence[str], None]` instead of `str | Sequence[str] | None` — low priority for migrations.
**Recommendation:** Update to modern union syntax.

### SEVERITY: Low
**File:** backend/tests/test_consistency.py
**Problem:** Reads frontend files from disk — fragile coupling to frontend file paths.
**Recommendation:** Make frontend source constants configurable or use a contract test approach.

### SEVERITY: Low
**File:** backend/app/admin_auth.py, backend/app/admin.py, backend/seed.py
**Problem:** No test coverage for admin authentication flow, admin panel setup, or seed script.
**Recommendation:** Add basic smoke tests for admin auth and seed idempotency.

### SEVERITY: Low
**File:** backend/app/config/{settings.py, db.py, exceptions.py, rate_limit.py}
**Problem:** Config modules have no dedicated unit tests.
**Recommendation:** Add unit tests for config validation, exception handlers, and rate limiter.

### SEVERITY: Low
**File:** backend/app/prices/router.py:26
**Problem:** Response model `list[PricePointRead] | list[PriceBucketRead]` — Union return type may confuse OpenAPI schema generation.
**Recommendation:** Consider a discriminated wrapper type.

### SEVERITY: Low
**File:** backend/seed.py:265
**Problem:** Individual `select(Item).where(Item.id == item_id)` inside price seeding loop — could be a single pre-fetch.
**Recommendation:** Pre-fetch all items mapped by name before the price-history loop.

### SEVERITY: Low
**File:** backend/alembic/versions/a1b2c3d4e5f6_add_basic_to_itemgrade_enum.py:21
**Problem:** Raw SQL `ALTER TYPE itemgrade ADD VALUE IF NOT EXISTS 'BASIC'` — unavoidable for PostgreSQL enum alteration.
**Recommendation:** Accept as necessary. Document the pattern.

---

## Frontend

### SEVERITY: Critical
**File:** frontend/src/lib/components/charts/EChartsLineChart.svelte:2
**Problem:** `// @ts-nocheck` disables all type checking for the entire chart component — hides type errors in formatters, parameters, `as` casts.
**Recommendation:** Remove `@ts-nocheck`, properly type all formatter callbacks (e.g. `TooltipFormatterParams[]` from echarts).

### SEVERITY: Critical
**File:** frontend/src/routes/items/[id]/+page.svelte:124
**Problem:** `(row: any) => ... as ChartPoint` — unsafe `as` cast on `any` without data shape validation.
**Recommendation:** Use a type guard or Zod schema to validate API response shape before casting.

### SEVERITY: Critical
**File:** frontend/src/routes/inventory/+page.svelte:68
**Problem:** `as InventoryItem[]` — unsafe `as` cast without validating structure of API response.
**Recommendation:** Add type guard validating `item_id`, `item_name`, `quantity` fields at runtime.

### SEVERITY: Critical
**Files:** ItemTable.svelte:102,126,199 | inventory/+page.svelte:51,97,103 | settings/+page.svelte:22
**Problem:** All 7 calls to `goto('/auth')` are not `await`ed — navigation may not complete before code continues execution.
**Recommendation:** Add `await` before every `goto('/auth')` call.

### SEVERITY: High
**File:** frontend/src/routes/items/[id]/+page.svelte:36-53
**Problem:** `computeNodeCost` function duplicated from `RecipeTree.svelte:19-33` — identical logic in two places.
**Recommendation:** Extract to shared utility `$lib/crafting-cost.ts` and import in both locations.

### SEVERITY: High
**File:** frontend/src/routes/items/[id]/+page.svelte:287-293
**Problem:** Currency display logic (gold/silver/bronze) duplicated from `ItemTable.svelte:298-312`.
**Recommendation:** Create a `<CurrencyDisplay coppers={value} />` component in `$lib/components/CurrencyDisplay.svelte`.

### SEVERITY: High
**File:** frontend/src/routes/inventory/+page.svelte:10-14
**Problem:** `CATEGORIES` array duplicated from `ItemTable.svelte:34-38` — same data in two files.
**Recommendation:** Extract `CATEGORIES` to `$lib/constants.ts`.

### SEVERITY: High
**File:** frontend/src/lib/components/ItemTable.svelte:178-194 and 196-204
**Problem:** `onMount` calls `loadSavedIds()` in `init()`, then `$effect` on line 196 also calls `loadSavedIds()` after `user` state settles — double call on startup.
**Recommendation:** Remove `loadSavedIds()` from `onMount.init()`, keep only in `$effect`.

### SEVERITY: High
**File:** frontend/src/lib/auth.svelte.ts:110
**Problem:** `logout` does not `await fetch('/auth/logout')` — network error during logout is silently ignored, server session may not be invalidated.
**Recommendation:** `await fetch(...)` before resetting state and redirecting.

### SEVERITY: High
**Problem (Cross-cutting):** Two sources of truth for grade colors: `layout.css:5-16` (CSS variables `--grade-*`) and `grades.ts:1-13` (`GRADE_COLORS`).
**Recommendation:** Centralize — either use only `gradeColor()` (removing CSS vars) or generate CSS vars from `grades.ts`.

### SEVERITY: Medium
**File:** frontend/src/routes/inventory/+page.svelte:42-74
**Problem:** `loadData` function has `try {} finally {}` without `catch` — network errors silently ignored, no error state in UI.
**Recommendation:** Add `catch` block setting `fetchError` state and displaying it in template.

### SEVERITY: Medium
**File:** frontend/src/routes/inventory/+page.svelte:95-99
**Problem:** `onMount` with auth guard is redundant — `$effect` on line 101 executes the same logic.
**Recommendation:** Remove `onMount` and its import; keep only `$effect`.

### SEVERITY: Medium
**File:** frontend/src/routes/+layout.svelte:9-11
**Problem:** `onMount(() => { checkMe(); })` — `$effect(() => { checkMe(); })` would work identically in Svelte 5.
**Recommendation:** Replace `onMount` with `$effect`.

### SEVERITY: Medium
**File:** frontend/src/routes/settings/+page.svelte:3
**Problem:** `import { onMount } from 'svelte'` — imported but never used (dead import).
**Recommendation:** Remove the unused `onMount` import.

### SEVERITY: Medium
**File:** frontend/src/lib/components/charts/EChartsLineChart.svelte:46,61,67,71,73
**Problem:** Formatter callbacks (`(params)`, `(v)`, `(p)`) lack type annotations (hidden by `@ts-nocheck`).
**Recommendation:** Add proper types after removing `@ts-nocheck`.

### SEVERITY: Medium
**Problem (Cross-cutting):** No `+error.svelte` file anywhere in the route tree — unhandled errors render as default SvelteKit error page.
**Recommendation:** Add `frontend/src/routes/+error.svelte` with basic error UI.

### SEVERITY: Low
**File:** frontend/src/routes/items/[id]/+page.svelte:204
**Problem:** `onMount` used for initial data load — `$effect` with guard on `page.params.id` would be more idiomatic Svelte 5.
**Recommendation:** Replace `onMount` with `$effect`.

### SEVERITY: Low
**File:** frontend/src/routes/items/[id]/+page.svelte:258
**Problem:** Complex inline `style="background:color-mix(...)"` — hard to maintain.
**Recommendation:** Extract to CSS class in `<style>` block.

### SEVERITY: Low
**File:** frontend/src/routes/inventory/+page.svelte:15-18
**Problem:** `GRADES` array in inventory includes 'Basic', while `ItemTable.svelte:40-43` does not — inconsistent grade filter options.
**Recommendation:** Extract shared `GRADES` list to `$lib/constants.ts`.

### SEVERITY: Low
**File:** frontend/src/routes/inventory/+page.svelte:31
**Problem:** `dataLoadStarted` as plain `let` instead of `$state` — anti-pattern in Svelte 5 for reactive guard.
**Recommendation:** Use `$state` or `$effect.pre` for the load guard.

### SEVERITY: Low
**File:** frontend/src/routes/inventory/+page.svelte:117-121
**Problem:** Filter inputs use only `placeholder` — no `<label>` elements for accessibility.
**Recommendation:** Add `<label class="sr-only">` or `aria-label` to each input.

### SEVERITY: Low
**File:** frontend/src/lib/auth.svelte.ts:25,36
**Problem:** `response.json()` in `fetchProfile` and `checkMe` not wrapped in try/catch — JSON parse error throws unhandled exception.
**Recommendation:** Add `try/catch` inside existing error handling blocks.

### SEVERITY: Low
**File:** frontend/src/lib/auth.svelte.ts:19
**Problem:** `const API_URL = API_BASE_URL` — unnecessary re-alias.
**Recommendation:** Remove `API_URL`, use `API_BASE_URL` directly.

### SEVERITY: Low
**File:** frontend/src/routes/auth/+page.svelte:2
**Problem:** `user` imported from `$lib/auth.svelte.js` but never used in template.
**Recommendation:** Remove unused `user` from the import.

### SEVERITY: Low
**File:** frontend/src/routes/+page.svelte:104
**Problem:** Price displayed as `item.current_price.toLocaleString()` instead of through `formatCurrency` — inconsistent with rest of app.
**Recommendation:** Use `formatCurrency(item.current_price)` for consistent currency formatting.

### SEVERITY: Low
**File:** frontend/src/lib/index.ts
**Problem:** Placeholder file with a comment, never imported by any file.
**Recommendation:** Delete or add re-exports (`export * from './currency.js'` etc.).

### SEVERITY: Low
**File:** frontend/src/routes/+layout.svelte:20-98
**Problem:** Root `<div class="min-h-screen...">` lacks semantic landmark role — `<main>` is nested inside.
**Recommendation:** Consider `role="application"` or `aria-label` on the main wrapper.

### SEVERITY: Low
**File:** frontend/src/routes/about/+page.svelte
**Problem:** Missing `<svelte:head>` with page title.
**Recommendation:** Add `<svelte:head><title>About — AA Tracker</title></svelte:head>`.

### SEVERITY: Low
**Problem (Cross-cutting):** SVG icons across the project lack `aria-hidden="true"` — screen readers may read them as separate elements.
**Recommendation:** Add `aria-hidden="true"` to all decorative SVGs.

---

## Discord Bot

### SEVERITY: High
**File:** discord_bot/cogs/prices.py:29-41
**Problem:** Bot uses "copper"/"c" suffix in `format_price`; frontend uses "bronze"/"b" — inconsistent terminology across product.
**Recommendation:** Rename to "bronze"/"b" to match frontend.

### SEVERITY: High
**File:** discord_bot/cogs/prices.py:29-41
**Problem:** `format_price` shows only non-zero denominations; frontend always pads silver to 2 digits and shows bronze — inconsistent display format.
**Recommendation:** Align formatting with frontend: pad silver to 2 digits, always show bronze.

### SEVERITY: High
**File:** discord_bot/cogs/prices.py (entire file)
**Problem:** No rate limiting awareness — rapid slash commands will trigger backend 429s caught as generic errors.
**Recommendation:** Add `commands.cooldown` or manual token-bucket per-user throttle.

### SEVERITY: Medium
**File:** discord_bot/cogs/prices.py:147-152, 197-202
**Problem:** HTTP 429 rate limit is caught by generic `httpx.HTTPError` handler and shown as "Backend connection error" — user unaware they're rate-limited.
**Recommendation:** Catch `httpx.HTTPStatusError` separately, check `response.status_code == 429`, show "Too many requests — slow down".

### SEVERITY: Medium
**File:** discord_bot/cogs/prices.py:147, 164, 197
**Problem:** No retry logic for transient failures (timeout, 503, connection reset) — a single blip loses user's price submission.
**Recommendation:** Add 1-2 retries with exponential backoff via `httpx.AsyncClient(transport=httpx.HTTPTransport(retries=2))`.

### SEVERITY: Medium
**File:** discord_bot/cogs/prices.py:147
**Problem:** `KeyError` from malformed API response is caught in same block as network errors — masks API contract breakage.
**Recommendation:** Separate `except KeyError` with distinct log warning "Unexpected API response shape".

### SEVERITY: Medium
**File:** discord_bot/tests/test_prices.py
**Problem:** No tests for: timeout scenarios, HTTP 429 rate-limit responses, malformed JSON body, `/addprice` path when backend rejects.
**Recommendation:** Add test cases for timeout, 429, JSONDecodeError, and backend-rejection in command handler path.

### SEVERITY: Low
**File:** discord_bot/cogs/prices.py:1
**Problem:** `from __future__ import annotations` is unnecessary on Python 3.13.
**Recommendation:** Remove the import.

### SEVERITY: Low
**File:** discord_bot/cogs/prices.py:52, 98
**Problem:** Each `lookup_item` and `post_price` call creates a new `httpx.AsyncClient` — wastes connection resources.
**Recommendation:** Pass a shared `httpx.AsyncClient` instance into the cog at init.

### SEVERITY: Low
**File:** discord_bot/bot.py:11,17
**Problem:** `DISCORD_GUILD_ID: str | None = None` — Pydantic-settings does not auto-coerce empty string to `None` for `str | None` when `str` is first.
**Recommendation:** Add `model_config = {"coerce_numbers_to_str": False}` or handle empty string explicitly.

### SEVERITY: Low
**File:** discord_bot/bot.py:31
**Problem:** `discord.Object(id=settings.guild_id)` — if `DISCORD_GUILD_ID` is non-integer string, `int()` on line 17 crashes without friendly error.
**Recommendation:** Wrap `int()` in try/except for clear startup error message.

---

## Infrastructure

### SEVERITY: Critical
**File:** infra/caddy/Caddyfile:7
**Problem:** `handle /admin*` uses Caddy `*` glob matching only non-slash characters — sub-paths like `/admin/items` do NOT match. Admin panel non-functional for sub-paths in production.
**Recommendation:** Replace with `handle /admin { ... }` and `handle /admin/* { ... }`.

### SEVERITY: Critical
**File:** infra/caddy/Caddyfile:7
**Problem:** Same `/admin*` glob incorrectly matches `/administration`, `/admin123`, `/admins` — any path starting with `/admin` followed by non-slash chars routes to admin backend.
**Recommendation:** Same fix — use exact `/admin` + `/admin/*` instead of greedy wildcard.

### SEVERITY: High
**File:** infra/compose/docker-compose.prod.yml:57
**Problem:** Caddy `depends_on: [backend, frontend]` has no `condition: service_healthy` — if backend hasn't bound port 8000 yet, Caddy serves 502 errors.
**Recommendation:** Add healthchecks to backend and frontend, then use `condition: service_healthy` on Caddy's depends_on.

### SEVERITY: High
**File:** infra/compose/docker-compose.prod.yml:18-34
**Problem:** Backend service has no `healthcheck` defined — no way for Docker to know if uvicorn is actually serving.
**Recommendation:** Add `healthcheck: { test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"], ... }`.

### SEVERITY: High
**File:** .gitignore
**Problem:** `.env.local` is NOT gitignored at root level — SvelteKit/Vite auto-loads `.env.local`, if created with secrets it would be committed.
**Recommendation:** Add `.env.local` and `.env.*.local` to root `.gitignore`.

### SEVERITY: Medium
**File:** infra/compose/docker-compose.dev.yml:29-30
**Problem:** Hardcoded fallback secrets `temporary-development-secret-must-be-32-chars` and `temporary-admin-session-secret-32-chars` — predictable for devs who forget env vars.
**Recommendation:** Use `${AUTH_SECRET:?}` fail-fast in dev too, or generate random defaults at container start.

### SEVERITY: Medium
**File:** infra/compose/docker-compose.dev.yml:8
**Problem:** Default `POSTGRES_PASSWORD=postgres` with no fail-fast — trivially guessable DB password.
**Recommendation:** Change to `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}`.

### SEVERITY: Medium
**File:** infra/compose/docker-compose.dev.yml:57-58
**Problem:** Frontend `depends_on: [backend]` without `condition: service_healthy` — frontend may start before backend is ready.
**Recommendation:** Add backend healthcheck and use `condition: service_healthy`.

### SEVERITY: Medium
**File:** .gitignore:177,190
**Problem:** `.idea/` and `.vscode/` are commented out — JetBrains/VS Code users without global gitignore will commit IDE settings.
**Recommendation:** Uncomment both lines.

### SEVERITY: Medium
**File:** Makefile:71-75
**Problem:** `test` target runs `uv run pytest` on host, not in container — requires full Python environment on host.
**Recommendation:** Run tests inside backend container or create dedicated `docker-compose.test.yml`.

### SEVERITY: Medium
**File:** Makefile:78-81
**Problem:** `migrate` and `seed` targets use `exec backend` with no pre-check — fails silently if backend container isn't running.
**Recommendation:** Add guard checking container status before `exec`.

### SEVERITY: Medium
**File:** backend/Dockerfile:12-14
**Problem:** `seed.py` not `COPY`d into container image — `make seed` against prod container fails because file doesn't exist in image.
**Recommendation:** Add `COPY seed.py ./seed.py` to Dockerfile.

### SEVERITY: Low
**File:** .env.example:11
**Problem:** Contains hardcoded `temporary-development-secret-must-be-32-chars` as documentation — encourages copy-paste without rotation.
**Recommendation:** Use `<generate-with-openssl-rand-hex-32>` placeholder instead.

### SEVERITY: Low
**File:** infra/caddy/Caddyfile:11
**Problem:** `handle /docs*` has same glob bug — matches `/documentation` but misses `/docs/oauth2-redirect`.
**Recommendation:** Replace with `handle /docs` + `handle /docs/*`.

### SEVERITY: Low
**File:** infra/compose/docker-compose.prod.yml:36-41
**Problem:** Frontend service has no healthcheck — Caddy can't verify Node process is serving on port 3000.
**Recommendation:** Add healthcheck with `wget -qO- http://localhost:3000 || exit 1`.

### SEVERITY: Low
**File:** .env.example
**Problem:** Missing entries for `COOKIE_SECURE` and `SQL_ECHO` — set in compose defaults but undocumented.
**Recommendation:** Add both with comments to `.env.example`.

### SEVERITY: Low
**File:** discord_bot/
**Problem:** No `.dockerignore` file — build context may include `.venv`, `__pycache__`, `.env`.
**Recommendation:** Create `discord_bot/.dockerignore` modeled after `backend/.dockerignore`.

### SEVERITY: Low
**File:** frontend/Dockerfile:27
**Problem:** `CMD ["node", "build"]` relies on Node auto-resolving `build/index.js` — fragile if output structure changes.
**Recommendation:** Use `CMD ["node", "build/index.js"]` for explicit entry point.

### SEVERITY: Low
**File:** .gitignore:211
**Problem:** `addon/archerage.log` is listed explicitly but `*.log` on line 60 already covers it — redundant.
**Recommendation:** Remove redundant line 211.

---

## Addon

### SEVERITY: Critical
**File:** addon/pricetracker/apitypes.lua, addon/pricetracker_1/apitypes.lua, addon/pricetracker_2/apitypes.lua, addon/pricetracker_3/apitypes.lua, addon/pricetracker_folio/apitypes.lua
**Problem:** All 5 copies of `apitypes.lua` are byte-identical (51KB each, same MD5). ~205KB of dead duplication.
**Recommendation:** Delete 4 copies, keep only `pricetracker_folio/apitypes.lua`.

### SEVERITY: Critical
**File:** addon/pricetracker_folio/buttoncommon.lua:2-13, addon/pricetracker_folio/button.lua:2-13
**Problem:** `dump()` and `SetButtonFontOneColor()` defined identically in both button.lua and buttoncommon.lua — conflicting definitions in the same load chain.
**Recommendation:** Remove duplicates from buttoncommon.lua (button.lua loads after and redefines them).

### SEVERITY: Critical
**File:** addon/pricetracker_folio/button.lua (810 lines), buttoncommon.lua (132 lines), window.lua (329 lines), windowcommon.lua (98 lines)
**Problem:** 1,369 lines of code copied verbatim from ArcheRage's Folio105 UI framework. These files reference 30+ framework globals (`F_COLOR.GetColor()`, `F_TEXT.ApplyAutoEllipsisTooltipText()`, etc.) not provided by the addon. If Folio105 is not loaded or changes, the addon silently breaks.
**Recommendation:** Document this dependency explicitly. Extract only the 3-4 functions actually used into a minimal `foliolib.lua` to reduce dependency surface.

### SEVERITY: High
**File:** addon/pricetracker_1/, addon/pricetracker_2/, addon/pricetracker_3/
**Problem:** Three prototype variants testing different UI approaches. Zero references from the canonical `_folio` version. Only unique code: `_3`'s `CHAT_MESSAGE` handler for `"!ptscan"`.
**Recommendation:** Delete all three prototype directories. Fold `!ptscan` chat trigger into `_folio` if desired.

### SEVERITY: High
**File:** addon/pricetracker_1/pricetracker.lua:17, addon/pricetracker_2/pricetracker.lua:17, addon/pricetracker_3/pricetracker.lua:17
**Problem:** `lastSweepRequestTime` variable assigned but never read back — dead assignment in all three prototypes.
**Recommendation:** Delete entire prototypes (above) or remove the dead variable.

### SEVERITY: High
**File:** addon/pricetracker_folio/pricetracker.lua:1
**Problem:** `_folio` is clearly canonical but has no version number, changelog, or deprecation markers. The older `pricetracker/` directory still has TESTING.md pointing to IT.
**Recommendation:** Add version comment header. Move TESTING.md to `_folio/` or update its references. Archive/delete `pricetracker/` as deprecated.

### SEVERITY: High
**File:** addon/pricetracker/TESTING.md:7
**Problem:** TESTING.md instructs users to install the OLD `pricetracker/` version, not the canonical `_folio`.
**Recommendation:** Move to `pricetracker_folio/TESTING.md` with updated paths and folio-specific test scenarios.

### SEVERITY: High
**File:** .gitignore
**Problem:** `prices.jsonl` files generated by all addon variants are NOT gitignored. Risk of leaking AH price data into repository.
**Recommendation:** Add `addon/**/prices.jsonl` and `addon/**/archerage.log` to `.gitignore`.

### SEVERITY: High
**File:** addon/pricetracker_folio/apitypes.lua:216,364,872
**Problem:** Three event key/value mismatches: `UPDATE_BUBBLE = "BUBBLE_UPDATE"`, `NPC_UNIT_EQUIPMENT_CHANGED = "UNIT_NPC_EQUIPMENT_CHANGED"`, `REPORT_BAD_USER_UPDATE = "BAD_USER_LIST_UPDATE"`.
**Recommendation:** Rename keys to match their string values.

### SEVERITY: High
**File:** addon/pricetracker_folio/toc.g:1-6
**Problem:** `buttoncommon.lua` loaded before `button.lua`, but `button.lua` redefines `dump()` and `SetButtonFontOneColor()` already present in `buttoncommon.lua` — silent shadowing risk.
**Recommendation:** Remove duplicate function definitions from buttoncommon.lua.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/button.lua:76
**Problem:** Leftover debug code: `X2Chat:DispatchChatMessage(CMF_SYSTEM, message)` inside `CreateButtonBgImg()` — logs every button creation texture path to system chat.
**Recommendation:** Remove debug chat dispatch or guard behind debug flag.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/button.lua:62-69
**Problem:** `InitButton()` function defined but never called anywhere — dead code from Folio105 framework.
**Recommendation:** Remove or add comment marking as available-for-use.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/window.lua:44-71, 177-218, 221-238, 241-274, 277-329
**Problem:** 5 factory functions from Folio105. Only `CreateEmptyWindow` is used by pricetracker.lua. Rest are dead code.
**Recommendation:** Split window.lua into used-only functions + archive, or add comment header listing used vs unused.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/pricetracker.lua:65-71
**Problem:** `jsonEscape()` function missing in `_folio` but present in old `pricetracker.lua`. Folio writes item names directly to JSONL without escaping — produces broken JSON for names containing `"` or `\`.
**Recommendation:** Add `jsonEscape()` to `_folio` and apply it before writing item names.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/pricetracker.lua:19-33
**Problem:** Watchlist items hardcoded in source. Requires Lua editing to change tracked items.
**Recommendation:** Load WATCHLIST from a JSON config file or addon settings API.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/pricetracker.lua:192
**Problem:** Magic number `999` for search duration, `1` for sort_kind — meanings undocumented.
**Recommendation:** Extract to named constants: `DURATION_ANY = 999`, `SORT_BY_NAME = 0`.

### SEVERITY: Medium
**File:** addon/pricetracker_folio/pricetracker.lua:87-90
**Problem:** Uses `parent:CreateIconDrawable("artwork")` — may not exist as standard API method; standard is `CreateImageDrawable()`.
**Recommendation:** Verify API method exists; replace with `CreateImageDrawable()` if not.

### SEVERITY: Medium
**File:** addon/pricetracker_3/pricetracker.lua:98
**Problem:** `CHAT_MESSAGE` handler fires on every chat message globally — potential performance issue on busy servers.
**Recommendation:** Add early return for system/battle channels to reduce overhead.

### SEVERITY: Low
**File:** addon/pricetracker_folio/button.lua:70
**Problem:** Garbage comment line: `-------------------------aaaaaaaaaaaaa...`
**Recommendation:** Delete the garbage comment.

### SEVERITY: Low
**File:** addon/pricetracker_folio/pricetracker.lua:74
**Problem:** Folio uses `os.date("!")` for timestamps while old `pricetracker.lua` uses `UIParent:GetServerTimeTable()` — should use server-authoritative time.
**Recommendation:** Use `UIParent:GetServerTimeTable()` in folio for authoritative timestamps.

### SEVERITY: Low
**File:** addon/pricetracker_folio/pricetracker.lua:174-183
**Problem:** `UpdateItemRow()` does exact string matching — fails if AH returns different casing or extra whitespace.
**Recommendation:** Use case-insensitive trimmed comparison for name matching.

### SEVERITY: Low
**File:** addon/pricetracker_folio/Icones/
**Problem:** Directory name typo — "Icones" should be "Icons" (English).
**Recommendation:** Rename to `icons/` and update references in `pricetracker.lua:24-26`.

### SEVERITY: Low
**File:** addon/pricetracker_folio/Icones/gold.dds, silver.dds, copper.dds
**Problem:** Game texture DDS files tracked in git — potential copyright concern, unnecessary binary bloat.
**Recommendation:** Document source (hand-made vs copied from game). If copied, remove from git and add to `.gitignore`.

### SEVERITY: Low
**File:** addon/pricetracker_folio/pricetracker.lua
**Problem:** No `LEFT_WORLD` or `UI_RELOADED` event handler — stale widgets left on UI reload (`/rl`).
**Recommendation:** Add cleanup handlers for `UIEVENT_TYPE.LEFT_WORLD` and `UIEVENT_TYPE.UI_RELOADED`.

### SEVERITY: Low
**File:** addon/pricetracker/TESTING.md:11-47
**Problem:** Test scenarios missing for folio version: window toggle, refresh cooldown, currency display, save behavior.
**Recommendation:** Add folio-specific test scenarios after moving TESTING.md.

---

## Cross-Domain Observations

1. **Currency display duplication (Frontend ↔ Bot):** Both frontend (`formatCurrency`) and Discord bot (`format_price`) implement currency formatting independently, with inconsistent suffixes ("bronze" vs "copper", "b" vs "c") and different display rules (padding, zero denominations).

2. **DRY violations across the stack:** Backend's `utcnow()` ×5 mirrors Frontend's `computeNodeCost` ×2 and `CATEGORIES`/`GRADES` ×2 — same anti-pattern: utility functions duplicated instead of extracted to shared modules.

3. **No shared config between bot and backend:** Bot's `GRADE_INT_TO_STR` and backend's `grade_map.py` must be kept in sync manually. No contract test validates they match at build time.

4. **Frontend ↔ Backend type gap:** `api.d.ts` is auto-generated but frontend code uses raw `as` casts without runtime validation. Backend changing a field type silently breaks UI rendering.

5. **Addon dependency on Folio105:** The addon's 1369 lines of framework code depend on a game-internal UI library — this is the riskiest single dependency in the entire project. If the game updates, the addon breaks.

6. **Missing `.env.example` documentation:** Three `.env.example` files exist (root, backend, frontend) but are incomplete — `COOKIE_SECURE`, `SQL_ECHO`, and `DISCORD_GUILD_ID` are undocumented. Discord bot config is entirely separate with no `.env.example` at all.

7. **Test infrastructure fragility:** Backend tests read frontend files from disk (`test_consistency.py`). Backend `make test` runs on host, not in container. No CI configuration exists anywhere.

8. **No automated testing for addon:** The only domain with zero automated tests. Manual test plan only covers the deprecated prototype version.
