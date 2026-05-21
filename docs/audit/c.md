# Full Codebase Audit — qwen3.6-plus — 2026-05-20

ArcheRage Market Tracker — Backend (FastAPI + SQLModel), Frontend (SvelteKit 5 + TS), Discord Bot (discord.py)

---

## Executive Summary

| Component | Critical | Warning | Suggestion | Info |
|---|---|---|---|---|
| **Backend** | 5 | 22 | 22 | 30 |
| **Frontend** | 11 | 18 | 22 | 24 |
| **Discord Bot** | 4 | 10 | 12 | 17 |
| **TOTAL** | **20** | **50** | **56** | **71** |

### Top Critical Issues (must fix)

| # | Problem | Component | File |
|---|---|---|---|
| 1 | `authentication_backend` assigned twice — dead code + security misconfig | Backend | `admin_auth.py:46,67` |
| 2 | `SecureAdminAuth.middlewares` never attached — session cookie security not applied | Backend | `admin_auth.py:51-64` |
| 3 | `match_or_create_item` commits mid-function — breaks atomic ingest | Backend | `ingest/services.py:46` |
| 4 | Price bucketing creates tz-aware datetimes, silently strips | Backend | `prices/services.py:60-64` |
| 5 | CORS overly permissive (`*` methods/headers) | Backend | `main.py:36-37` |
| 6 | `@ts-nocheck` in EChartsLineChart — all type checking disabled | Frontend | `EChartsLineChart.svelte:2` |
| 7 | Explicit `any` types, unsafe type assertions | Frontend | multiple |
| 8 | Dead `svelte:window` binding, fragile `$effect` guards | Frontend | multiple |
| 9 | Missing `SubmitEvent` imports | Frontend | `auth/+page.svelte`, `settings/+page.svelte` |
| 10 | No shared HTTP client — connection churn per API call | Discord Bot | `cogs/prices.py:52,98` |
| 11 | No global command error handler — silent failures | Discord Bot | `cogs/prices.py` |
| 12 | Deprecated `tree.copy_global_to()` | Discord Bot | `bot.py:33` |
| 13 | No empty-name validation | Discord Bot | `cogs/prices.py:146` |

---

## Backend Audit

### Critical

- [admin_auth.py:46,67] `authentication_backend` assigned twice — first at line 46 (`AdminAuth`), then overwritten at line 67 (`SecureAdminAuth`). The first assignment is dead code that could mislead developers into thinking the simpler auth is active. **Fix:** remove line 46.
- [admin_auth.py:51-64] `SecureAdminAuth` defines `self.middlewares` but this attribute is **never used** by sqladmin's `AuthenticationBackend`. The SessionMiddleware must be attached to the FastAPI app, not stored on the auth backend. This means session cookies may not have `https_only` or `same_site` settings applied in production. **Fix:** attach SessionMiddleware to the app in `setup_admin()` or `main.py`.
- [ingest/services.py:46] `match_or_create_item` calls `await session.commit()` mid-function (after the upsert), then `add_price_point` is called later which also commits. If `add_price_point` fails, the item is already committed — creating orphaned items with no price history. This breaks the atomic ingest contract. **Fix:** remove the commit from `match_or_create_item`; let `bulk_ingest` or `add_price_point` handle the commit, or wrap the entire row processing in a sub-transaction.
- [prices/services.py:60-64] Bucketing logic converts naive DB timestamps to timezone-aware for epoch calculation, then creates `bucket_start` as tz-aware datetime. These are returned in `PriceBucketRead` as naive `datetime` fields — the tzinfo is silently stripped by Pydantic serialization, potentially causing off-by-hour bugs for non-UTC clients. **Fix:** keep everything naive-UTC throughout, or explicitly strip tzinfo before creating `PriceBucketRead`.
- [app/main.py:36-37] CORS allows `allow_methods=["*"]` and `allow_headers=["*"]` — all HTTP methods and headers are permitted from any configured origin. While origins are restricted, this is overly permissive and could allow unexpected methods (DELETE, PATCH) from the frontend origin. **Fix:** restrict to `["GET", "POST", "PUT", "PATCH", "OPTIONS"]` and explicit header list.

### Warning

- [profiles/models.py:7, items/models.py:7, prices/models.py:6, user_items/models.py:7] **Duplicated `utcnow()` function** — identical `datetime.now(timezone.utc).replace(tzinfo=None)` defined in 4 separate model files. Violates DRY. **Fix:** extract to `app/utils/time.py` or `app/config/db.py`.
- [auth/manager.py:10] Cross-module import: `from app.profiles.models import Profile` — imports a model directly from another module, violating the constitution rule. **Fix:** import through `app.profiles.services`.
- [prices/services.py:6] Cross-module import: `from app.items.models import Item` — direct model import from another domain module. **Fix:** use `app.items.services.get_item()`.
- [user_items/services.py:7-8] Cross-module imports: `from app.items.models import Item, ItemCategory, ItemGrade` and `from app.items.schemas import ItemListItem, PaginatedItems`. **Fix:** either import through items.services or accept as read-only dependency.
- [user_inventory/services.py:8-9] Cross-module imports from crafting module. **Fix:** create a crafting service facade or accept as read-only dependency.
- [ingest/services.py:15-17] Cross-module imports — most cross-module-dependent service. Acceptable for ingest (pipeline orchestrator), but document the dependency graph.
- [profiles/services.py:18, user_items/services.py:78, user_inventory/services.py:50,63, prices/services.py:123] **Service-layer commits** — inconsistent: some services commit, some don't. **Fix:** establish a clear convention and document it.
- [admin_auth.py:22-23] Broad `except Exception` in login flow swallows all errors. **Fix:** catch specific exception types, or log before returning False.
- [prices/services.py:23-24] `to_naive()` helper defined **inside** `get_item_price_history()`. **Fix:** move to module scope.
- [prices/services.py:49-53] `INTERVAL_SECONDS` dict recreated on every call. **Fix:** move to module-level constant.
- [ingest/services.py:88-93, 101-107] Broad `except Exception` in `_process_row`. **Fix:** catch specific exceptions (IntegrityError, OperationalError).
- [auth/manager.py:30] `print(f"User {user.id} has registered.")` — debug print in production code. **Fix:** use `logging.info()`.
- [calculator.py:1] Unnecessary file path comment at top of file. **Fix:** remove.
- [profiles/router.py:9] Unused import: `from app.users.models import User`. **Fix:** remove.
- [settings.py:14-15] Default secrets are weak defaults that could accidentally leak to staging. **Fix:** add runtime warning when defaults are used.
- [calculator.py:75] Magic number: `depth >= 10` — hardcoded recursion limit. **Fix:** extract to `MAX_RECIPE_DEPTH = 10`.
- [ingest/services.py:65] Magic value: `timedelta(hours=1)` tolerance. **Fix:** move to settings or document.
- [items/services.py:15] Default `limit=20` hardcoded in function signature and router — could drift. **Fix:** use shared constant `DEFAULT_PAGE_SIZE = 20`.

### Suggestion

- [prices/services.py:49-53] Use `match` statement instead of dict lookup for interval mapping.
- [ingest/grade_map.py:4-17] `GAME_GRADE_TO_ENUM` dict could use `match` or `IntEnum`.
- [calculator.py:47-51] Profit calculation ternary → `match` or explicit `if/else`.
- [items/models.py:11-24] `ItemCategory` enum values contain spaces — error-prone for string comparison.
- [profiles/services.py:10-21] `get_or_create_profile` does two queries — optimize with `RETURNING`.
- [crafting/services.py:13-20] `load_all_recipes` / `load_all_items` load ALL rows into memory — won't scale.
- [prices/services.py:34] Price history buckets in Python — use SQL `GROUP BY` with `date_trunc`.
- [user_inventory/models.py:6-12] Missing `created_at` / `updated_at` timestamp fields.
- [main.py:24-25] Empty `lifespan` context manager — consider removing if unused.
- [pyproject.toml:5] `description = "Add your description here"` — placeholder not updated.

### Info (positive patterns)

- [config/rate_limit.py] Singleton limiter — correct.
- [main.py:43-52] All API routes under `/api/`, admin at `/admin` — correct.
- [user_inventory/router.py:21,32] Route order: `/for-recipe` before `/{item_id}` — correct.
- [ingest/router.py:12-13] No auth + rate limit on ingest — correct.
- [ingest/services.py:102] `session.rollback()` after failed `add_price_point` — correct.
- [user_inventory/services.py:44-63] Upsert pattern correct — DELETE for 0, ON CONFLICT for >0.
- [prices/services.py:104-107, 117-121] Naive UTC + atomic current_price update — correct.
- All tests use real PostgreSQL, UUID suffixes — correct.
- Alembic migration chain linear and complete.
- Modern Pydantic v2, StrEnum, pydantic-settings patterns used throughout.

### Missing Test Coverage

| Module | Gap |
|---|---|
| `app/admin.py` (setup_admin) | No tests |
| `app/config/exceptions.py` | No tests |
| `app/config/rate_limit.py` | No tests |
| `app/auth/backend.py` | No tests |
| Rate limiting (ingest, prices) | No tests |
| `admin_auth.py` (SecureAdminAuth) | No tests |
| Concurrent inventory upsert | No tests |
| `seed.py` | No tests |
| `alembic/` migrations | No reversibility tests |

---

## Frontend Audit

### Critical

- [EChartsLineChart.svelte:2] `// @ts-nocheck` disables ALL TypeScript checking for the entire file.
- [items/[id]/+page.svelte:123] `(row: any)` — explicit `any` bypasses type system.
- [ItemTable.svelte:228] `<svelte:window bind:scrollY />` — dead binding, never used.
- [inventory/+page.svelte:101-108] `$effect` with boolean guard — fragile state management, will break if auth state changes mid-session.
- [settings/+page.svelte:12-17] `$effect` syncs `user.profile` into local `$state` without cleanup — divergence risk.
- [auth/+page.svelte:10] `handleSubmit(e: SubmitEvent)` — `SubmitEvent` not imported.
- [settings/+page.svelte:26] `handleSave(e: SubmitEvent)` — same issue.
- [ItemTable.svelte:108] `data.items as ItemListItem[]` — unsafe type assertion.
- [inventory/+page.svelte:68] `as InventoryItem[]` — same unsafe assertion.
- [items/[id]/+page.svelte:104] `item = await r.json()` — no type assertion.
- [items/[id]/+page.svelte:141] `craftTree = await r.json()` — no type assertion.

### Warning

- [items/[id]/+page.svelte:36-53] `computeNodeCost` duplicated verbatim in `RecipeTree.svelte:19-33`.
- [inventory/+page.svelte:10-14] `CATEGORIES` array duplicated from `ItemTable.svelte:34-38`.
- [inventory/+page.svelte:15-18] `GRADES` array duplicated from `ItemTable.svelte:40-43`.
- [ItemTable.svelte:279-311] Inline currency formatting — violates patterns.md ("historical bug: local copy of splitCurrency").
- [items/[id]/+page.svelte:286-296] Same inline currency formatting instead of `formatCurrency`.
- [+page.svelte:104] `item.current_price.toLocaleString()` — raw copper, not formatted.
- [auth.svelte.ts:68,84,101] `error.detail` — no type guard; FastAPI returns string or object.
- [auth.svelte.ts:27,44, ItemTable.svelte:71,117,157] `catch (e)` — `e` is `unknown` in strict mode.
- [items/[id]/+page.svelte:122-126] Price history mapping relies on union of two response shapes without discrimination.
- [ItemTable.svelte:206-213] `$effect` triggers `loadItems()` — potential duplicate fetches.
- [inventory/+page.svelte:95-99] `onMount` and `$effect` do same check — race condition possible.
- [ItemTable.svelte:84-88] `URLSearchParams` — magic strings for parameter names.
- [items/[id]/+page.svelte:12-18] `SOURCE = 'ah'` should be shared constant.
- [grades.ts:16] `gradeColor(grade: string)` — should be typed as `ItemGrade`.
- [ItemTable.svelte:97] Double-slash URL risk if `apiEndpoint` starts with `/`.

### Suggestion

- [items/[id]/+page.svelte] 367 lines — split into sub-components or extract composables.
- [ItemTable.svelte] 344 lines — extract `useVirtualScroll` and `useItemFetching` composables.
- [auth.svelte.ts] Extract typed `apiFetch<T>()` wrapper — eliminate 10+ repetitive fetch blocks.
- [EChartsLineChart.svelte] Remove `@ts-nocheck`, add proper type annotations.
- [+page.svelte:84] Use keyed each `{#each items as item (item.id)}`.
- [ItemTable.svelte:84] `limit = 100` is `$state` but never changes — should be `const`.
- [inventory/+page.svelte:29] `debounceTimers` never cleaned up on unmount.
- [settings/+page.svelte:44] `setTimeout` never cleaned up.
- [ItemTable.svelte:187-192] Resize listener not passive.
- [+layout.svelte:54] `email?.[0].toUpperCase()` — throws if email is empty string.
- [RecipeTree.svelte:17] `DEPTH_COLORS` — hardcoded, should be CSS custom properties.
- [ItemTable.svelte:46-47] `ROW_HEIGHT = 72`, `VISIBLE_COUNT = 20` — magic numbers.
- [RecipeCard.svelte:73,84] Batch size `max="999"` — should be named constant.
- [grades.ts] Missing `Basic` grade color — falls back to same as `Grand`.
- [items/[id]/+page.svelte:204-210] No error boundary for parallel async calls.
- [config.ts] `PUBLIC_API_URL` fallback includes `/api` — double-prefix risk.
- Custom `<style>` blocks should be Tailwind utilities.

### Info (positive patterns)

- Auth state uses `$state<UserState>` singleton — correct Svelte 5 runes.
- All fetches use `credentials: 'include'` — correct for JWT cookie auth.
- `formatCurrency` and `splitCurrency` are single source of truth.
- `LABOUR_ITEM_NAME` single exported constant.
- Virtual scrolling with `$derived` — correct runes usage.
- `$derived.by()` for expensive calculations — proper memoization.
- `#snippet` for recursive tree rendering — correct Svelte 5 pattern.
- `checkMe()` in `onMount` — correct one-time init (not in `$effect`).
- Good accessibility: `aria-label`, label/input pairing.
- Grade color CSS custom properties in `:root`.
- `strict: true`, `moduleResolution: "bundler"` — correct for SvelteKit 5.

---

## Discord Bot Audit

### Critical

- [cogs/prices.py:52,98] **New `httpx.AsyncClient` per API call — no connection pooling.** Under concurrent usage causes connection churn and can exhaust ephemeral ports. **Fix:** use single shared client as cog attribute.
- [cogs/prices.py:109-179] **No global command error handler.** Unexpected exceptions cause deferred interaction to hang until timeout. **Fix:** add `on_app_command_error` listener.
- [bot.py:33] **`tree.copy_global_to()` is deprecated in discord.py 2.4+.** **Fix:** use `await self.tree.sync(guild=guild)` directly.
- [cogs/prices.py:146] **No validation for empty/whitespace-only `name`.** Results in confusing backend rejection. **Fix:** validate before API call.

### Warning

- [cogs/prices.py:145-152,162-173] Duplicated error-handling boilerplate between `/addprice` and `/price`. **Fix:** extract `_handle_backend_error()` helper.
- [cogs/prices.py:155,175,204] `GRADE_INT_TO_STR[grade].lower()` repeated 4 times. **Fix:** extract `grade_label()` helper.
- [cogs/prices.py:52,98] No retry logic for backend calls. **Fix:** simple retry with backoff (2-3 attempts).
- [cogs/prices.py:122-129] `grade` parameter accepts any int — backend validates 0-11, bot should too.
- [bot.py:13] `API_URL` default includes `/api` suffix — fragile if changed. **Fix:** store base URL without `/api`.
- [tests/test_prices.py] Tests call `.callback()` directly, bypassing discord.py argument validation.
- [tests/test_prices.py] Missing error path tests: HTTP errors, backend rejection, malformed responses.
- [cogs/prices.py:141] Magic number: `999_999 * 10000` — no explanation.
- [cogs/prices.py:11] Unused import: `datetime` (only `timezone` needed).

### Suggestion

- Add `cog_unload` to close shared HTTP client.
- Subclass `commands.Bot` with typed `api_url` property.
- Load `GRADE_CHOICES` from backend at startup.
- Add command cooldowns (`@app_commands.checks.cooldown`).
- Extract test fixtures to `conftest.py`.
- Use Pydantic model for `lookup_item` return type.
- Configurable log level from env var.
- Add ruff lint rules: `select = ["E", "F", "I", "UP", "B"]`.

### Info (positive patterns)

- `Settings` uses pydantic-settings with env vars — no hardcoded secrets.
- `setup_hook` for cog loading and command sync — proper async lifecycle.
- `defer(ephemeral=True)` for slow operations — prevents timeout.
- `source="ah"` consistent with constitution.
- Proper `setup` function for cog registration.
- `format_price` thoroughly tested.
- `lookup_item` tests cover exact match, case-insensitive, suggestions, grade mismatch.
- `post_price` tests verify payload, HTTP errors, backend rejection, timezone.
- Minimal, focused dependencies.
- `asyncio_mode = "auto"` for pytest-asyncio.
- Dockerfile uses official `uv` image with Python 3.13.

---

## Cross-Cutting Observations

### What's Good
- Constitution invariants correctly implemented (naive UTC, singleton limiter, partial-success ingest, upsert patterns, route order)
- All API endpoints have test coverage on real PostgreSQL
- Svelte 5 runes used correctly (`$state`, `$derived`, `$derived.by`)
- Modern Pydantic v2, SQLModel, StrEnum patterns
- Clean module structure with self-contained domains
- `formatCurrency` and `LABOUR_ITEM_NAME` as shared constants (mostly respected)
- OpenAPI type generation → `api.d.ts` — no manual API types

### Systemic Issues
| Issue | Scope | Impact |
|---|---|---|
| Duplicated `utcnow()` | Backend (4 files) | DRY violation, maintenance risk |
| Cross-module model imports | Backend (5 modules) | Violates constitution, tight coupling |
| Inline currency formatting | Frontend (3 locations) | Violates patterns.md, display inconsistency risk |
| Duplicated `computeNodeCost` | Frontend (2 files) | DRY, bug divergence risk |
| Unsafe type assertions | Frontend (3+ files) | Runtime errors hidden from compiler |
| No shared HTTP client | Discord Bot | Performance, scalability |
| Missing error handlers | Backend + Discord Bot | Silent failures |
| Service-layer commit inconsistency | Backend (5+ services) | Transaction isolation issues |

### Dead Code Confirmed
- `mockData.ts` — already deleted (roadmap item resolved)
- `InventoryModal.svelte` — already deleted (roadmap item resolved)
- `admin_auth.py:46` — dead `AdminAuth` assignment (needs removal)
- `profiles/router.py:9` — unused `User` import
- `cogs/prices.py:11` — unused `datetime` import
