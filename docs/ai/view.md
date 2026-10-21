# Architecture review and target design (Stage 1)

Date: 2026-10-21. Scope: read-only review of `main` (`991397e`) plus the working tree. Nothing in the code was changed.

The data source is moving away from the `pricetracker_folio` addon (writing JSONL, later fed in by the Discord bot or a POST). The new source is the CSV files written by the **ArcheMarket** addon (`listings.csv`, `market.csv`). The user uploads them by hand in the browser.

> **Working tree is not clean.** Uncommitted deletions already exist: `addon/`, `discord_bot/`, `.idea/`, `CLAUDE.md`, `.claude/settings.json`, `.env.example`, `backend/.env.example`, `frontend/.env.example`. `infra/.env.example` is untracked and identical to the old root `.env.example`. This review reads the deleted files from `HEAD`. Deleting `frontend/.env.example` breaks CI (`.github/workflows/frontend.yml:32` runs `cp .env.example .env`). Deleting `CLAUDE.md` drops the project rules for agents.

---

## 1. Current architecture (as the code has it)

### 1.1 Backend modules and DB schema

FastAPI app with all routers under `/api` (`backend/app/main.py:50-60`) and sqladmin at `/admin` (`backend/app/admin.py:74-81`). Each module has models/schemas/services/router.

| Table | Module | Columns (key ones) | Constraints / relations |
|---|---|---|---|
| `user` | users | `id uuid`, `email`, `hashed_password`, `is_active`, `is_superuser`, `is_verified` | `email` unique (`users/models.py:6-12`) |
| `profile` | profiles | `user_id`, `is_private`, `display_name`, `avatar_url`, timestamps | `user_id` FK unique, 1:1 (`profiles/models.py:11-18`) |
| `item` | items | `id`, `name`, `category` enum, `grade` enum, `current_price`, `last_price_at`, timestamps | `UNIQUE(name, grade)` (`items/models.py:43-53`) |
| `pricepoint` | prices | `item_id`, `source`, `price`, `captured_at`, `created_at` | FK item; **no unique key** (dupes allowed) (`prices/models.py:10-16`) |
| `useritem` | user_items (watchlist) | `user_id`, `item_id`, `created_at` | `UNIQUE(user_id, item_id)` (`user_items/models.py:11-17`) |
| `recipe` | crafting | `item_id`, `output_qty` | `item_id` unique, 1 recipe per item (`crafting/models.py:5-8`) |
| `recipeingredient` | crafting | `recipe_id`, `ingredient_item_id`, `quantity` | `UNIQUE(recipe_id, ingredient_item_id)` (`crafting/models.py:11-21`) |
| `userinventory` | user_inventory | `user_id`, `item_id`, `quantity` | `UNIQUE(user_id, item_id)` (`user_inventory/models.py:6-13`) |

`ingest` has no tables. It maps an int grade to `ItemGrade` (`ingest/grade_map.py:4-17`, where 0 = Basic) and finds or creates items by case-insensitive name + grade (`ingest/services.py:20-56`).

Endpoints:

| Route | Auth | Source |
|---|---|---|
| `POST /api/auth/{login,register,forgot-password,reset-password}` (throttled) + fastapi-users auth/register/reset/verify routers | public | `auth/router.py:27-140` |
| `GET/PATCH /api/users/me`, `/api/users/{id}` (fastapi-users) | user / superuser | `auth/router.py:141-145` |
| `GET /api/me` | user | `users/router.py:10` (duplicate, unused by the frontend) |
| `GET/PATCH /api/profiles/me` | user | `profiles/router.py:14-29` |
| `GET /api/items/`, `GET /api/items/{id}` | public | `items/router.py:13-45` |
| `GET /api/items/{id}/price-history?source&from&to&interval` | public | `prices/router.py:24-43` |
| `POST /api/items/{id}/prices` | user, 60/min | `prices/router.py:46-65` |
| `GET /api/crafting/`, `POST /api/crafting/{id}/calculate` | **public** | `crafting/router.py:12-25` |
| `/api/user-items/{me,ids,{id}}` | user | `user_items/router.py:14-65` |
| `/api/inventory/`, `/for-recipe/{id}`, `PUT /{id}` | user | `user_inventory/router.py:13-42` |
| `POST /api/ingest/prices` | **Bearer `INGEST_TOKEN`**, 60/min | `ingest/router.py:13-24`, `ingest/dependencies.py:8-13` |
| `/admin` | superuser session; Caddy IP allowlist in prod | `admin_auth.py:92-147`, `infra/caddy/Caddyfile:25-29` |

### 1.2 Price data flow (end to end)

1. The `addon/pricetracker_folio/pricetracker.lua:18,297` addon appended JSONL to `prices.jsonl`. The watcher that used to tail that file has already been removed (`docs/ai/architecture.md:91`).
2. The Discord bot (`/addprice`), or any client holding `INGEST_TOKEN`, sends `POST /api/ingest/prices` with up to 100 rows: `{name, grade:int, price, ts, source}` (`ingest/schemas.py:6-15`).
3. `bulk_ingest` handles one row at a time (`ingest/services.py:112-134`): it finds or creates the item, then calls `add_price_point`. That inserts a `PricePoint` and does a guarded `UPDATE item.current_price` when the new row is newer (`prices/services.py:96-136`). Each row commits on its own, and a failure rolls back that row only.
4. Reads: `price-history` loads every row in the range and buckets them in Python (`prices/services.py:12-93`). The frontend asks for `source='ah'` (`frontend/src/routes/items/[id]/+page.svelte:15`, guarded by `backend/tests/test_consistency.py`).
5. Crafting and the item pages read `Item.current_price` (`crafting/calculator.py:46,89`).
6. `backend/seed.py` loads 29 items, the Blazing Sunridge recipe tree and 30 days of random price walk.

Since the watcher went away and the bot is being removed, nothing feeds real prices into this pipeline any more.

### 1.3 Auth: who can do what

- fastapi-users with a JWT in a cookie, lifetime 1 h (`auth/backend.py:9-23`).
- Login is limited to 5/min, register / forgot / reset to 5/hour (`auth/router.py:27-114`).
- `current_user` does **not** check `active` (`auth/dependencies.py:23`). A deactivated user's JWT keeps working until it expires. Login does block inactive users (`auth/router.py:36`).
- Anonymous users can read items, price history and the crafting calculator.
- A logged-in user can manage their own watchlist, inventory and profile, and can POST manual price points.
- A superuser can use `/admin` (sqladmin, mostly read-only views) and the fastapi-users `/users/{id}` routes.
- Ingest needs only the shared Bearer token, with no user attached.
- Forgot-password creates a token, but no `on_after_forgot_password` hook delivers it (`auth/manager.py:14-44`), so users cannot actually reset a password.

### 1.4 Frontend

SvelteKit with Svelte 5 runes, `adapter-node`, Tailwind 4 + DaisyUI (`night` theme), TypeScript.

| Route | What it does |
|---|---|
| `/` | Hero, plus "Hot deals", which is really just the first 3 items by name, shown as raw copper with `¤` (`routes/+page.svelte:12,104`) |
| `/items` | `ItemTable`: search/category/grade filters, virtual scroll, follow toggle (`lib/components/ItemTable.svelte`) |
| `/items/[id]` | Item card, market price, 7D/30D/90D/MAX line chart, recipe tree with profit and an inventory "Have" column (`routes/items/[id]/+page.svelte`) |
| `/saved-items` | `ItemTable` on `/user-items/me` |
| `/inventory` | Inventory editor; loads every item 200 at a time (`routes/inventory/+page.svelte:49-63`) |
| `/settings`, `/auth`, `/about` | Profile edit, login/register, static page |

- **State:** user state is created per request and passed through Svelte context (`lib/auth.svelte.ts:27-56`), checked once in `+layout.svelte:11-13`. There is no store library. Each page keeps its own local `$state`.
- **API types:** generated into `lib/api.d.ts` and re-exported from `lib/types.ts`.
- **Charts:** ECharts 6 through `svelte-echarts` (`lib/components/charts/EChartsLineChart.svelte`). It draws one smoothed line plus a dashed material-cost `markLine`. It is marked `@ts-nocheck` and uses a light tooltip on a dark theme.
- **API base URL:** `$env/static/public` `PUBLIC_API_URL`, baked in at build time, falling back to `http://localhost:8000/api` (`lib/config.ts:1-7`).
- **CSP:** emitted by SvelteKit with `connect-src 'self'` (`svelte.config.js:11-21`).

### 1.5 Infra and CI

- **Dev compose** (`infra/compose/docker-compose.dev.yml`): `db`, `backend` (`--reload`, bind mounts), `frontend` (node:22 running `npm run dev`), and `discord_bot` behind the `bot` profile (`:61-71`).
- **Prod compose** (`docker-compose.prod.yml`): `db`, `backend` (2 workers, proxy headers), `frontend` (node build), `discord_bot` (**not** behind a profile, and `DISCORD_TOKEN` is required: `:50-60`), and `caddy`.
- **E2E compose:** `db-e2e:5433`, `backend-e2e:8001`, `frontend-e2e:5174`.
- **Caddy:** TLS, HSTS and security headers. `/api/*` goes to the backend, `/admin*` to the backend behind an IP allowlist, everything else to the frontend. Docs are not routed (`Caddyfile:18-37`).
- **Makefile:** dev/prod/e2e wrappers around `podman compose -f infra/compose/...`. `make test` starts the dev DB and runs pytest locally (`Makefile:72-76`). The e2e targets use `cd e2e` and `$(ROOT_DIR)e2e/fixtures.sql` (`Makefile:99-104`).
- **CI** (`.github/workflows`):
  - `backend.yml`: ruff, `uv lock --check`, pytest on Postgres 16, `alembic upgrade head` + `alembic check`.
  - `frontend.yml`: `npm ci` + `svelte-check` only.
  - `docker.yml`: builds both images, no push.
  - `discord_bot.yml`.
  - **No** vitest, Playwright or `infra/tests/*.sh` job.

### 1.6 Tests

- **Backend** (pytest, real Postgres `app_test`, `create_all` without alembic, `conftest.py:38-48`). About 140 tests: auth and rate limits, settings validator, items, prices (plus a race test), ingest (16 tests, plus auth and rate limit), crafting and calculator (cycles, depth), inventory (plus edge cases and races), watchlist (plus races), profiles, admin users, docs disabled in prod, and cross-file consistency.
- **Frontend** (vitest + jsdom + testing-library, about 54 tests): `currency`, `crafting.computeNodeCost`, `auth` state, `ItemTable`, `RecipeCard`, `RecipeTree`, `EChartsLineChart`, and a smoke test for each route page. CI never runs them.
- **E2E** (Playwright, 20 tests in `e2e/`): auth, items list and detail, follow/unfollow, crafting tree with inventory, rate-limit message, inventory error toast, auth redirect. They need `make e2e-up`, `e2e-migrate` and `e2e-seed`, and CI does not run them.
- **Infra:** four grep-based shell checks (`infra/tests/`), which nothing runs.

---

## 2. Assessment

### 2.1 What is good (keep it)

- The module layout is consistent (models / schemas / services / router / admin) and easy to extend (`docs/ai/patterns.md:3-19`).
- Atomic `INSERT … ON CONFLICT` patterns are already used (`user_inventory/services.py:54-63`, `user_items/services.py:71-79`, `ingest/services.py:39-46`). The idempotent CSV import needs exactly this.
- Tests run against a real Postgres, with race tests. CI runs `alembic check`, which catches model/migration drift (`.github/workflows/backend.yml:118-125`).
- Production hardening is in place:
  - the settings validator rejects default or short secrets in prod (`config/settings.py:241-268`);
  - docs are off in prod (`main.py:28-35`);
  - Caddy sets headers and an admin IP allowlist;
  - Dockerfiles run as non-root;
  - auth is rate-limited.
- ECharts is already a dependency, so a line + bar chart needs no new library.
- The API types are generated (`openapi-typescript`), so frontend/backend drift shows up in `svelte-check`.

### 2.2 Debt and bugs

| # | Problem | Where |
|---|---|---|
| D1 | The e2e frontend points at the **dev** backend. Compose sets `PUBLIC_API_BASE_URL`, but the app reads the build-time `PUBLIC_API_URL`, which is empty, so it falls back to `localhost:8000`. | `infra/compose/docker-compose.e2e.yml:38`, `frontend/Dockerfile:11-12`, `frontend/src/lib/config.ts:7` |
| D2 | CSP `connect-src 'self'` blocks API calls whenever the frontend and API are on different origins (e2e 5174→8001; dev 5173→8000 too, if SvelteKit applies CSP in dev, which is **unverified**). Prod is fine because Caddy serves both on one origin. | `frontend/svelte.config.js:17` |
| D3 | CI runs no vitest, no Playwright and no `infra/tests`, so nothing shows the e2e suite has ever passed (D1 suggests it cannot). | `.github/workflows/frontend.yml:34-36` |
| D4 | `docker.yml` triggers on a PR only when a Dockerfile changes, not when code changes. | `.github/workflows/docker.yml:13-16` |
| D5 | `pricepoint` has no unique key, so re-sending the same data duplicates it. Not idempotent. | `backend/app/prices/models.py:10-16` |
| D6 | `current_user` does not require an active user. | `backend/app/auth/dependencies.py:23` |
| D7 | The password reset flow is dead: no hook delivers the token. | `backend/app/auth/manager.py:14-44` |
| D8 | `/api/me` duplicates `/api/users/me`. The frontend uses only the second. | `backend/app/users/router.py:10`, `frontend/src/lib/auth.svelte.ts:64` |
| D9 | `ItemFilter` and `UserItemRead` are unused schemas. | `backend/app/items/schemas.py:34`, `backend/app/user_items/schemas.py:8` |
| D10 | The home page formats prices by hand instead of using `formatCurrency` (a constitution rule). | `frontend/src/routes/+page.svelte:104` |
| D11 | The `Basic` grade is missing from the frontend grade list and colours, although the backend enum has it. | `frontend/src/lib/components/ItemTable.svelte:42-45`, `frontend/src/lib/grades.ts` |
| D12 | The prod compose requires `DISCORD_TOKEN`, so `make prod-up` fails without a bot. | `infra/compose/docker-compose.prod.yml:50-60` |
| D13 | Where compose reads `.env` from: with `-f infra/compose/*.yml`, compose looks for `.env` in `infra/compose/`, not in the repo root or `infra/`. The Makefile passes no `--env-file`. **Needs checking with podman compose.** | `Makefile:2-3` |
| D14 | The Makefile `help` does not list the e2e targets. The e2e targets use relative `cd e2e` while everything else uses `$(ROOT_DIR)`. | `Makefile:11-29`, `Makefile:101-104` |
| D15 | A no-op `lifespan`, and `getattr(settings, "environment", "dev")` on a typed field. | `backend/app/main.py:23-28` |
| D16 | `@sveltejs/adapter-auto` is an unused devDependency. | `frontend/package.json:18` |
| D17 | IDE folders are tracked (`backend/.idea/`), and plans live in two places (`docs/ai/superpowers/` and `docs/superpowers/`). `backend/README.md` is empty. | `git ls-files` |

### 2.3 Docs that disagree with the code

| Doc says | Code does | Refs |
|---|---|---|
| The ingest endpoint has no auth | Bearer `INGEST_TOKEN` | `docs/ai/constitution.md:8`, `docs/ai/architecture.md:24` vs `ingest/router.py:16` |
| `/api/prices/` is an authenticated write | `POST /api/items/{id}/prices` | `architecture.md:26` vs `prices/router.py:14,46` |
| Crafting is authenticated | Crafting is public | `architecture.md:27` vs `crafting/router.py:12-25` |
| Auth state is a global singleton in `auth.svelte.js` | Per-request state passed by context, in `auth.svelte.ts` | `architecture.md:80`, `patterns.md:78` vs `lib/auth.svelte.ts:27-56` |
| `current_active_user` exists | Only `current_user` / `current_superuser` exist | `patterns.md:40-42` vs `auth/dependencies.py:23-24` |
| ECharts 5.6, TS ≥6.0, SvelteKit ≥2.57 | `echarts ^6.1`, `typescript ~5.6`, `@sveltejs/kit ^3.1` | `stack.md:23-29` vs `frontend/package.json` |
| Prod runs 4 services | Prod runs 5 (plus `discord_bot`) | `stack.md:38`, `constitution.md:44` vs `docker-compose.prod.yml` |
| `ItemTable` has a local copy of `splitCurrency` | It imports it from `$lib/currency` | `patterns.md:74` vs `ItemTable.svelte:7` |
| `feature/user-inventory` is waiting to merge; clean up `mockData.ts`, `InventoryModal.svelte`, `aiosqlite` | Already merged (`d0175bf`), and none of those three exist | `roadmap.md:28,36-38`, `progress.md` (stale since 2026-05-20) |
| `admin/` is a module | It is two files: `app/admin.py` and `app/admin_auth.py` | `architecture.md:62` |

### 2.4 Dead or unneeded once the data source changes

| What | Why it goes | Refs |
|---|---|---|
| `discord_bot/` (whole folder) | Its only job was `/price` and `/addprice` against the old API | `.github/workflows/discord_bot.yml`, compose dev `:61-71`, prod `:50-60`, `infra/tests/test_compose_has_discord.sh`, `infra/tests/test_dockerfiles_non_root.sh:4` |
| `addon/` (pricetracker, `_1`, `_2`, `_3`, `_folio`) | Replaced by ArcheMarket (separate repo) | — |
| `backend/app/ingest/` (+ `INGEST_TOKEN`) | Only the bot, the watcher and the tests call it | `main.py:14,59`, `config/settings.py:205,212,232,248`, `docker-compose.prod.yml:35`, `infra/.env.example` (`INGEST_TOKEN`), tests `test_ingest.py`, `test_ingest_auth.py`, `test_rate_limit_ingest.py`, `test_settings_validator.py:57` |
| `backend/app/prices/` (`PricePoint`, `price-history`, `POST prices`) | The new market and listing tables replace it | `admin.py:70,77`, `alembic/env.py:10`, `tests/test_prices*.py`, `tests/test_consistency.py`, `seed.py` price history |
| `Item.current_price` / `last_price_at` and the `ItemCategory` / `ItemGrade` enums | The CSV gives an `item_type` int and an `item_grade` int (ITEM_GRADE_TYPE, where 0 = NONE, which is what Leather gives). This does not match `grade_map` (0 = Basic). The CSV has no category. | `items/models.py:11-53`, `ingest/grade_map.py:4-17` |
| `EChartsLineChart.svelte` (+ test) and the range buttons on `/items/[id]` | Replaced by one 14-day chart (line + bar) | `routes/items/[id]/+page.svelte:15-21,94-114` |
| Plans and specs for discord-bot, pricetracker-folio, ingest | They describe removed components | `docs/ai/superpowers/{plans,specs}/2026-05-1{6,7}-*` |

---

## 3. Data contract (ArcheMarket, verified against the sample files)

Sample: `ArcheMarket/llm-wiki/sources/raw/ingame/2026-10-21-step7b/`, 3 scans, 10 real items plus `Nonexistent Item`.

- `listings.csv` (250 rows): `scan_id,captured_at,item,status,rank,unit_price_copper,listing_price_copper,stack`. **It has no `item_type` or `item_grade`, only the name.** A non-`ok` status gives one row with `rank=0` and empty prices (in the sample, `Nonexistent Item,no_result`).
- `market.csv` (406 rows): `scan_id,captured_at,item,item_type,item_grade,status,day,daily_avg_copper,weekly_avg_copper,min_copper,max_copper,volume`. When `ok`, there are 14 rows per item per scan. **Items with no exact-name search row get no line at all** (`Nonexistent Item` is absent). That follows `step7b-design.md` goal 4.
- Day 14 is today, a partial day (answered in ArcheMarket `open-questions.md` #11: Leather's volume grew between scans). Day 1..13 values stayed the same across scans.
- `captured_at` differs per item inside one scan, and `scan_id` is the scan start time.

---

## 4. Target architecture

### 4.1 What stays, what goes, what changes

| Area | Decision |
|---|---|
| Stays as is | `config/`, `auth/` + `users/` (fastapi-users), `admin.py` / `admin_auth.py`, Caddy, the compose layout, Alembic, the pytest-on-Postgres approach, the SvelteKit + DaisyUI + ECharts stack, `currency.ts` |
| Removed | `discord_bot/`, `addon/`, `ingest/`, `prices/`, `INGEST_TOKEN`, the bot CI job, compose services and infra checks, `EChartsLineChart`, the docs of removed components |
| Changed | `items/` (new natural key), `seed.py` (load the sample CSVs instead of a random walk), e2e fixtures, `/items/[id]` page, `test_consistency.py` |
| New | `market/` backend module (import, queries) and frontend routes `/import` and `/market` |
| Waiting for your decision | crafting, inventory, watchlist, profiles (section 4.6) |

### 4.2 Schema (proposal)

```
item          id PK, item_type int NULL, item_grade int NULL, name text NOT NULL, created_at
              UNIQUE(item_type, item_grade)       -- natural key from market.csv
              UNIQUE(name)                        -- listings.csv only has the name
market_day    item_id FK, day date, daily_avg, weekly_avg, min, max, volume (bigint),
              scan_id bigint, captured_at timestamp
              PRIMARY KEY (item_id, day)
listing       scan_id bigint, item_id FK, rank smallint, captured_at timestamp, status text,
              unit_price, listing_price, stack (NULL when status != ok)
              PRIMARY KEY (scan_id, item_id, rank)
```

- **Merging market data:**

  ```
  INSERT … ON CONFLICT (item_id, day) DO UPDATE SET … WHERE EXCLUDED.captured_at > market_day.captured_at
  ```

  The newest scan wins for each (item, date). Day 14 grows during the day. Older days come out identical, so they count as "skipped".
- **Day date:** `date(captured_at) - (14 - day)`. Which timezone this uses is an open question (Q2).
- **Listings:** `ON CONFLICT DO NOTHING`. Uploading the same file again inserts 0 rows. "Current cheapest offers" means the rows from the newest `scan_id` for that item.
- **Matching items by name:** `market.csv` creates and updates `item` (it has `item_type` / `item_grade` and the name). `listings.csv` matches by exact name, which is how the addon matches names too (ADR 0002). A listing name with no market row (`no_result`, `not_on_page1`) creates an item with `item_type NULL`. A later market row for the same name fills it in.

**Trade-off on `UNIQUE(name)`:** one name per item, so two grades with the same name cannot both exist. The addon cannot tell them apart in listings either: it takes the first exact-name row. If you start tracking graded gear, that changes to `UNIQUE(name, item_grade)`, and listings get matched through the same scan's market row.

**Alternative:** keep listings keyed by name only, with no FK. That is simpler, but then the item drop-down needs a join by name, and renames get messy.

### 4.3 Import

- `POST /api/market/import`, multipart, one or more files, **superuser only**, with a size cap (for example 5 MB per file).
- The file type is detected from the exact header row. Anything else is rejected with 400.
- Parsing uses the stdlib `csv` module, so RFC 4180 quoted names work.
- Each file runs in one transaction, in bulk (`executemany` / multi-row insert, no per-row commit).
- When both files are sent together, `market.csv` is processed first, so items get their `item_type` before listings match them.
- Response, one entry per file:

  ```
  {file, kind, rows, inserted, updated, skipped, errors:[{line, reason}]}
  ```

  - `skipped` counts duplicates, older data and `no_answer` / `error` rows.
  - `errors` lists malformed rows. Those rows are skipped and the rest of the file still imports, the same as the old partial-success contract.
- **No upload-log table.** Idempotency comes from the table keys alone. This is the minimal option. A log (file name, sha256, who, when, counts) would give an import history page, so add it only if you want one.

### 4.4 Read API

| Endpoint | Returns |
|---|---|
| `GET /api/market/items` | Items for the drop-down (id, name, last day) |
| `GET /api/market/items/{id}/days?days=14` | `[{day, daily_avg, weekly_avg, min, max, volume}]` |
| `GET /api/market/summary` | One row per item: `today_avg`, `avg_7d`, `change_pct`, `sold_today`, `avg_daily_volume` |
| `GET /api/market/items/{id}/listings` | The newest scan's offers: `scan_id`, `captured_at`, status, ranks |

Proposed summary definitions (Q3):
- "today" is the item's newest `market_day`;
- `avg_7d` is that day's `weekly_avg` from the game, the same number as the chart's second line;
- `change_pct = (today_avg - avg_7d) / avg_7d`;
- `sold_today` is today's volume, which is partial;
- `avg_daily_volume` is the mean volume of the 7 full days before today, which leaves out the partial day.

### 4.5 Frontend

- `/market`, the new main page:
  - an item `<select>` at the top;
  - one ECharts chart: `daily_avg` and `weekly_avg` as 2 lines on the left y-axis, `volume` as bars on the right y-axis, 14 days. It needs `BarChart` registered, and nothing new to install;
  - the cheapest current offers for the selected item;
  - the "today vs 7d" table for all items below that.
- `/import`, superuser only: a drop zone plus `<input type="file" multiple accept=".csv">`, and a summary table for each file.
- `/items`, `/items/[id]`, `/saved-items` and `/inventory` depend on the module decisions in 4.6.

### 4.6 Other modules: fit and proposal (nothing gets deleted without your OK)

| Module | Fit with the new data | Proposal |
|---|---|---|
| auth / users / admin | Needed: the upload must be restricted | **Keep.** Make upload superuser-only. Consider closing public registration, since this is one user's app |
| crafting | Needs a price for each ingredient. Recipes exist only in `seed.py`, for items that are not in the favorites. Admin cannot create recipes (`crafting/admin.py:11-13`) | **Freeze**: hide it from the nav, keep the code. When it comes back, the buy price is the cheapest listing `unit_price` and the sell price is `daily_avg` |
| inventory | Built on the recipe tree (`user_inventory/services.py:76-103`). ArcheMarket step 7c (bag prices) will be the real source for it | **Freeze** until 7c |
| watchlist (`user_items`) | `favorites.txt` in the addon already decides which items are tracked, so every imported item is watched | **Remove** (after your OK) |
| profiles | `display_name` and `is_private` are shown nowhere | **Remove** with the settings page (after your OK), or keep it if you plan public profiles |

### 4.7 Structure clean-up

| Change | Paths to update |
|---|---|
| Move `e2e/` to `frontend/e2e/` and merge it into `frontend/package.json` (`@playwright/test` and `tsx` as devDeps, a `test:e2e` script). Keep `frontend/e2e/tsconfig.json`. `frontend/tsconfig.json` includes only `src/**`, and vitest includes only `src/**/*.test.ts`, so nothing collides | `Makefile:99-104`, `frontend/.dockerignore` (add `e2e`, `test-results`, `playwright-report`), `frontend/.gitignore`, docs |
| Make `infra/.env.example` the only env template (already done in the working tree) | Restore `frontend/.env.example` **or** change CI to `echo PUBLIC_API_URL=… > .env` (`frontend.yml:32`). Make the Makefile pass `--env-file $(ROOT_DIR)infra/.env` (D13). Remove `INGEST_TOKEN` and `DISCORD_*` |
| Fix e2e wiring | `docker-compose.e2e.yml:33-38`: use a build arg `PUBLIC_API_URL=http://localhost:8001/api`, or route e2e through one origin |
| Add CI jobs | vitest (`npm test`) in `frontend.yml`. Playwright as a non-blocking job. Run `infra/tests/*.sh` |
| Repo hygiene | Untrack `backend/.idea/` and ignore `.idea/`. Put all plans and specs under `docs/ai/` (merge `docs/superpowers/` into it). Restore `CLAUDE.md` with the new rules (no Discord bot section, no ingest) |
| Fix D4, D12, D14 | Trigger `docker.yml` on code changes too. Drop the bot from the prod compose |

### 4.8 Open questions (your call)

1. **DB data:** is the current prod or dev data worth keeping? If not, write one new baseline migration and wipe the DB (simplest). If yes, write a migration that keeps the users.
2. **Timezone for `day`:** UTC, the ArcheRage server time, or Europe/Warsaw? This matters for scans near midnight.
3. **Summary definitions** (4.4): use the game's `weekly_avg` for "7d", or our own mean of 7 `daily_avg` values? Should "average per day" leave out today?
4. **Item key:** `UNIQUE(name)` plus `(item_type, item_grade)` (recommended for now), or `(name, item_grade)`?
5. **Read access:** should `/market` be public, or only for logged-in users?
6. **Modules:** freeze crafting and inventory, and remove watchlist and profiles (4.6)?
7. **`/items` list:** keep it (it would become the drop-down data), or merge it into `/market`?
