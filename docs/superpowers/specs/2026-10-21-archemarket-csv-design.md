# Design: ArcheMarket CSV as the price source

Date: 2026-10-21. Status: draft, waiting for the user's approval. Two independent reviews (Fable and Opus) have been folded in.
Background reading: [`docs/view.md`](../../view.md), the stage 1 review of the current code. Its recommendations were accepted, and this document overrides it wherever the two differ.
Data contract: the ArcheMarket repo (`/home/kstasica/projects/ArcheMarket/llm-wiki`), mainly `project/step7-design.md`, `project/step7b-design.md`, `open-questions.md` #10–11, the sample files in `sources/raw/ingame/2026-10-21-step7b/`, and `addon/archemarket/main.lua`.

## 1. Intent

The app (FastAPI + SvelteKit 5 + Postgres) shows ArcheRage auction house prices. The old way data came in no longer works:
- the `pricetracker_folio` Lua addon wrote JSONL;
- a watcher daemon (already removed) or a Discord bot sent it to `POST /api/ingest/prices`.

The user now runs their own addon, **ArcheMarket**. It scans up to 50 favourite items once or twice a day and appends what it sees to two CSV files. Every so often the user will **drag and drop those files onto a page**, and the app turns them into charts.

It is one person's tool, and the user wants it calm and orderly. They want to see:
- what one item has cost over 14 days and how much of it sold;
- which items are moving today compared with the last week;
- what the cheapest offers on the AH are right now.

The user also wants the codebase cleaned up: a symmetric, predictable layout with code split by domain, the same files in every module, and tests that mirror the code.

## 2. Goals

### 2.1 Remove

The working tree already has some of these deleted, uncommitted, by the user.

1. `discord_bot/` and everything that exists only for it:
   - `.github/workflows/discord_bot.yml`;
   - the `discord_bot` service in dev and prod compose;
   - `infra/tests/test_compose_has_discord.sh`;
   - the `discord_bot/Dockerfile` entry in `infra/tests/test_dockerfiles_non_root.sh`.
2. `addon/` (all `pricetracker*`).
3. `backend/app/ingest/` and `INGEST_TOKEN`: settings, `.env.example`, prod compose, and tests (`test_ingest*.py`, `test_rate_limit_ingest.py`, and the `ingest_token` argument in the settings test).
4. `backend/app/prices/` (`PricePoint`, `price-history`, `POST /items/{id}/prices`), its tests and admin view, and `test_consistency.py`.
5. The watchlist (`backend/app/user_items/`) and profiles (`backend/app/profiles/`), including the `on_after_register` / `on_before_delete` profile hooks in `auth/manager.py`, their routes and tests, and the frontend pages `/saved-items` and `/settings`.
6. **Account flows a single-user app does not need.** Public registration, and the forgot-password, reset-password and verify routers (nothing ever delivered their tokens; view D7). Also `test_password_reset.py`, `register()` in `frontend/src/lib/auth.svelte.ts`, and the Register tab on `/auth`.
7. The old `items/` module (merged into `market/`, §2.3), the old frontend price chart (`EChartsLineChart.svelte` + test), and the old `/items` and `/items/[id]` pages.
8. Docs and plans about removed parts: the discord-bot, pricetracker-folio and ingest specs and plans.
9. Leftovers named in the review:
   - unused `ItemFilter`;
   - the `/api/me` duplicate;
   - the no-op `lifespan`;
   - the `adapter-auto` devDependency;
   - tracked `backend/.idea/`.

**Rule:** the full delete list is shown to the user and confirmed before anything is deleted.

### 2.2 Freeze (keep the code, switch it off)

`crafting` and `inventory` stay in the repo and get **rebuilt from scratch later**. To make that impossible to break or reach by accident, the frozen code moves **out of the built and tested trees**:

```
backend/frozen/   crafting/  inventory/  tests/        (was app/crafting, app/user_inventory, their tests)
frontend/frozen/  crafting/  inventory/                 (RecipeCard, RecipeTree, crafting.ts, the /inventory page, their tests)
```

- Each folder gets a `FROZEN.md`: one paragraph saying why it is frozen, that it is to be rebuilt, and that it is kept as a reference only.
- Nothing imports frozen code:
  - it is outside `app/` and `src/`;
  - pytest `testpaths` stays `tests`;
  - vitest includes only `src/**`;
  - svelte-check and `vite build` cover only `src/`.

  So none of it is mounted, has tables, gets type-checked or is reachable by URL.
- Ruff excludes `backend/frozen/`. It still imports names that no longer exist, such as `ItemCategory` and `current_price`.
- The e2e spec `crafting-inventory.spec.ts` moves to `frontend/frozen/e2e/`.
- `docs/roadmap.md` gets an entry: "Rebuild crafting and inventory on the new item and price model (reference: `backend/frozen`, `frontend/frozen`)".

### 2.3 Move and restructure

**Backend layout** (agreed with the user; `items/` merged into `market/` after review):

```
backend/app/
├── main.py            only builds the app and mounts routers
├── core/              shared plumbing, no domain logic
│   ├── settings.py  db.py  errors.py  rate_limit.py  time.py (single utcnow)
├── admin/             setup.py (register views) + auth.py (sqladmin login)
├── auth/              User model + fastapi-users wiring (users/ merged in)
│   ├── models.py  schemas.py  router.py  admin.py
│   └── backend.py  manager.py  dependencies.py  cli.py (create-superuser)
└── market/            items, market days, listings, CSV import
    ├── models.py  schemas.py  services.py  router.py  admin.py
    └── csv_format.py  pure CSV parsing/validation, unit-tested without a DB

backend/tests/         mirrors app/
├── conftest.py
├── core/  auth/  admin/
└── market/
    ├── fixtures/      real ArcheMarket CSV samples (copied in) + small hand-made edge-case files
    └── test_csv_format.py  test_import.py  test_queries.py
```

Rules for this layout:
- Every domain module has the core file set: `models`, `schemas`, `services`, `router`, `admin` where it needs one.
- **Every extra file needs a one-line reason**, written as the first line of the file:
  - `auth/` has the fastapi-users wiring (`backend`, `manager`, `dependencies`) and `cli`;
  - `market/` has `csv_format`.
- A module never imports another module's models, only its services. Foreign keys to another module's tables are allowed.
- Test file names follow `test_<subject>.py`.
- `items/` is merged into `market/` because no endpoint of its own is left. Item upserts must run inside market's per-file transaction, and the summary query joins items with market days. When crafting is rebuilt it can reference `item.id` through an FK.

**Frontend layout:**

```
frontend/src/
├── lib/core/          api config, auth state, currency, grades, generated api types
├── lib/market/        MarketChart, SummaryTable, ListingsTable, ImportDropzone (+ tests next to them)
├── routes/            / (redirects to /market), /market, /import, /auth, /about
└── test/              mocks + route tests
frontend/e2e/          Playwright (moved from /e2e)
frontend/frozen/       see §2.2
```

- **E2E:** `e2e/` moves to `frontend/e2e/` and joins `frontend/package.json` (`@playwright/test` and `tsx` become devDependencies, plus a `test:e2e` script). It keeps its own `tsconfig.json`. Vitest and svelte-check must not pick up e2e or frozen files.
- **Env:**
  - `infra/.env.example` is the only env template.
  - The Makefile passes `--env-file $(ROOT_DIR)infra/.env` to compose **only when that file exists**, so a fresh clone still starts on the defaults.
  - Frontend CI no longer copies `frontend/.env.example`; it writes the one variable it needs.
- **Docs:** everything lives under `docs/`, with `docs/superpowers/` merged in.
- **`CLAUDE.md`** is restored and rewritten for the new layout and rules.

### 2.4 New data model

```
item        id PK, item_type int NULL, item_grade int NULL, name text NOT NULL, created_at
            UNIQUE (item_type, item_grade)      -- natural key from market.csv
            UNIQUE (name)                       -- listings.csv carries only the name
market_day  item_id FK→item, day date, daily_avg bigint, weekly_avg bigint, min bigint,
            max bigint, volume bigint, scan_id bigint, captured_at timestamp (naive UTC)
            PRIMARY KEY (item_id, day)
listing     item_id FK→item, scan_id bigint, rank smallint, captured_at timestamp (naive UTC),
            status text, unit_price bigint NULL, listing_price bigint NULL, stack int NULL
            PRIMARY KEY (item_id, scan_id, rank)
```

- Money and volume use `bigint`. A listing can be worth more than 2³¹ copper: a stack of 10 000 at 100 g a unit is 10¹⁰ c.
- `item_grade` stays the raw game int (`ITEM_GRADE_TYPE`; 0 for Leather). Nothing maps it to an enum. The old `ItemCategory` / `ItemGrade` enums and `current_price` / `last_price_at` are gone.
- **One new baseline migration replaces every existing migration.** The current DB data is not kept.
  - Existing dev, e2e and prod volumes must be dropped. An old `alembic_version` makes `alembic upgrade head` fail, so the backend container crash-loops.
  - Add `make dev-reset` (`down -v`, then up) and a release note.
  - The test `setup_database` fixture runs `DROP SCHEMA public CASCADE; CREATE SCHEMA public` instead of `drop_all`, because old tables with FKs to `item` would otherwise block it on existing local `app_test` databases.

### 2.5 CSV import

- **`POST /api/market/import`:**
  - multipart, one or more files;
  - **superuser only**;
  - rate limit 10/min through the single limiter;
  - per-file size cap of 50 MB. The addon appends every scan, so the files grow by roughly 1,100 rows per scan, and at 50 items × 2 scans a day that reaches 50 MB in about 15 months. The import is idempotent, so `docs` tell the user that old CSVs can be archived or emptied at any time.
- **Detecting the file type:** the first line must equal one of the two headers below exactly (the same strings as `main.lua:16-17`). Otherwise the file is rejected with a per-file error, and the other files still import.
  - `listings`: `scan_id,captured_at,item,status,rank,unit_price_copper,listing_price_copper,stack`
  - `market`: `scan_id,captured_at,item,item_type,item_grade,status,day,daily_avg_copper,weekly_avg_copper,min_copper,max_copper,volume`
- **Parsing:** stdlib `csv` (RFC 4180, so quoted names with commas work), UTF-8 with a possible BOM. Epoch seconds become naive UTC `datetime`.
- **Row validation** (in `csv_format.py`). A bad row becomes an error `{line, reason}` and is skipped; the rest of the file still imports.
  - `listings`, `status=ok`: needs `rank ≥ 1` and every price and stack present and ≥ 0.
  - `listings`, `status ∈ {no_buyout, not_on_page1, no_result, error}`: needs `rank = 0` and empty prices.
  - `market`, `status=ok`: needs `day ∈ 1..14` and every value present and ≥ 0. All zeros is valid, because that is what the server answered.
  - `market`, `status ∈ {no_answer, error}`: needs `day = 0` and empty values. These rows are counted as `skipped` and not stored.
  - Any other status is an error.
- **Items** (resolved in Python once per distinct item in the file, at most about 50, inside the file's transaction):
  - Postgres `ON CONFLICT` can only target one unique key per statement, so a single upsert cannot handle both keys.
  - A **market** row looks the item up by `(item_type, item_grade)`, then by `name`:
    - found by type and grade: update its `name` if it changed;
    - found by name with NULL type: fill in `item_type` and `item_grade` on that same row (no second item, so nothing needs merging);
    - not found: insert it.
  - A **listings** row looks the item up by exact `name`. If none exists, it inserts the item with NULL type and grade.
  - A market row whose `name` already belongs to an item with a **different non-null** `(item_type, item_grade)` becomes a row error with the reason "name already used by another grade". This covers both a graded item (Q6) and a rename onto a name already taken.
  - Because lookups go both ways, the order of files in a request does not matter.
- **Market merge:**
  - `day_date = date(captured_at in Europe/Moscow) − (14 − day)` (the server's clock, §8 Q2).
  - Rows are **deduplicated in memory by `(item_id, day_date)`**, keeping the newest `captured_at`. A full-history file holds many scans on many dates, so the same `day` index means different dates, while the same date appears in many scans. Postgres rejects an `ON CONFLICT DO UPDATE` that touches the same row twice in one statement.
  - Then upsert on `(item_id, day)`. Overwrite only when the incoming `captured_at` is newer than the stored one.
- **Listings merge:** bulk insert with `ON CONFLICT DO NOTHING`.
- **Transactions and speed:**
  - one transaction per file;
  - bulk statements (multi-row insert in chunks), never one commit per row;
  - a database failure rolls back that file only and is reported as a file-level error.
- **Response:** one entry per file, `{filename, kind, rows, inserted, updated, skipped, error_count, errors: [{line, reason}]}`.
  - `rows` counts data lines.
  - `inserted` + `updated` + `skipped` + `error_count` = `rows`.
  - `skipped` covers in-file duplicates, rows older than or equal to the stored ones, and `no_answer`/`error` lines.
  - `errors` lists at most the first 100.
- **Expected results on the real samples** (verified by both reviewers; these become the `test_import.py` assertions):

  | Upload | File | Rows | Inserted | Updated | Skipped |
  |---|---|---|---|---|---|
  | First | `market.csv` | 406 | 140 | 0 | 266 |
  | First | `listings.csv` | 250 | 250 | 0 | 0 |
  | Second, same files | both | | 0 | 0 | all |

  A hand-made fixture spanning **two dates** must cover the date dedup, because the samples all fall on one date.
- **Idempotency:** a second upload of the same file changes neither the counts nor the table contents. No upload-history table: the keys alone give idempotency.

### 2.6 Read API (`/api/market/...`)

| Endpoint | Returns |
|---|---|
| `GET /items` | Every item that has market or listing data: `id, name, item_type, item_grade, last_day`, sorted by name |
| `GET /items/{id}/days?days=14` | The last N `market_day` rows, oldest first: `day, daily_avg, weekly_avg, min, max, volume` |
| `GET /items/{id}/listings` | Rows from this item's newest `scan_id`: `scan_id, captured_at, status, rank, unit_price, listing_price, stack` |
| `GET /summary` | One row per item, described below |

`/summary` columns. "Today" means the item's newest `market_day`, and "the 7 days" means the 7 full days before it:
- `day`: that date;
- `today_avg` = its `daily_avg`;
- `avg_7d` = the `weekly_avg` of the **day before today**. The game's `weekly_avg` for day N is the volume-weighted mean of days N−6..N, verified on the samples (Leather, day 14: 4877 in the file, 4876 computed). Taking the day before keeps the partial day out;
- `change_pct = (today_avg − avg_7d) / avg_7d`, or null when `avg_7d = 0` or missing;
- `sold_today` = its `volume`, which is partial;
- `avg_daily_volume` = mean `volume` over the same 7 full days.

Reading these endpoints needs no login.

### 2.7 Frontend pages and auth

- **`/market`, the main page. `/` redirects here.** From top to bottom:
  1. An item drop-down (`<select>`, sorted by name). The selection is kept in the URL query (`?item=<id>`), so the page can be linked and reloaded.
  2. One ECharts chart over 14 days:
     - lines for `daily_avg` and `weekly_avg` on the left y-axis (in g/s/b, using `formatCurrency`);
     - `volume` as bars on the right y-axis;
     - the tooltip shows all three values plus min and max;
     - dark-theme colours.
  3. The cheapest current offers for the item: a table of rank, unit price, stack and listing price, with the scan time above it. A non-`ok` status is shown as words ("no buyout", "not on page 1", "no result").
  4. The "today vs 7 days" table for all items, with the columns from 2.6. It is sortable by any column, and clicking a row selects that item.
- **`/import`, superuser only, linked in the nav only for a superuser:**
  - a drop zone plus `<input type="file" multiple accept=".csv">`;
  - after an upload, a summary table for each file (the numbers from 2.5) and its error list;
  - non-superusers get a "not allowed" message.
- **Auth:**
  - `/auth` is login only.
  - `UserRead` gains `is_superuser`, so the frontend can show `/import`. It is the user's own flag. The tests that assert the old shape change to match (`test_user_read_schema.py`, `test_auth.py`).
  - **`python -m app.auth.cli create-superuser EMAIL PASSWORD`** creates the superuser, or resets the password if the user already exists, so it also serves as the password reset. It lives under `app/`, so it runs in the dev, e2e and prod images. Wrapped as `make create-superuser EMAIL=… PASSWORD=…` (dev) and used by `make e2e-seed`.
  - Backend tests stop going through `/api/auth/register`. A `make_user(email, password, superuser=False)` helper writes the user straight to the DB (`PasswordHelper`, as `sample_user` already does) and the test logs in through the API. This affects `conftest.py` (`superuser_client`), `test_auth.py` and `test_admin_users.py`.
- Keep the existing conventions: `formatCurrency` from the shared lib, `credentials: 'include'`, types generated by `openapi-typescript`, DaisyUI `night`.

### 2.8 Seed, infra, CI

- **`make seed` (dev):**
  - `seed.py` imports the sample CSVs from `backend/tests/market/fixtures/` through the same import service. It creates no random prices.
  - The dev compose bind-mounts `../../backend/tests:/app/tests:ro`, because the image copies only `app/` and `alembic/`.
- **E2E data:**
  - The e2e stack seeds **only the superuser**, through the CLI. Market data arrives by upload inside the tests.
  - The market journey is **one serial spec file**: login, upload, re-upload, `/market` checks. Playwright `workers: 2` cannot then reorder it.
  - Because reruns reuse the DB, e2e asserts only the sum rule and "nothing new on the second upload". The exact counts stay in `test_import.py`.
- **CSP:**
  - `svelte.config.js` appends the origin of `PUBLIC_API_URL` to `connect-src`.
  - It reads `process.env.PUBLIC_API_URL`, with the same `http://localhost:8000/api` fallback as `lib/core/config.ts`.
  - Fable reports that SvelteKit emits the CSP header in dev too, so dev 5173→8000 is blocked today; Opus could not check this. The fix covers dev and e2e either way.
  - The e2e frontend image is built with `PUBLIC_API_URL=http://localhost:8001/api`.
  - Prod stays same-origin through Caddy.
- **Prod compose** loses the bot, so `make prod-up` no longer needs `DISCORD_TOKEN`.
- **CI:**
  - `frontend.yml` also runs `npm test` (vitest);
  - a new `e2e.yml` runs Playwright against `docker compose -f infra/compose/docker-compose.e2e.yml`. It is **non-blocking** (`continue-on-error`) for now;
  - `infra/tests/*.sh` run in CI;
  - `docker.yml` also triggers on code changes in PRs.
- **New e2e specs, replacing the removed ones:**
  - log in as the seeded superuser;
  - upload both sample CSVs, check the summary sums, then re-upload and check that nothing new is inserted;
  - `/market` shows the chart, the offers and the summary table;
  - picking another item updates the chart and the offers;
  - an anonymous user can see `/market` but not `/import`.

### 2.9 Docs

- Rewrite `docs/architecture.md`, `stack.md`, `patterns.md`, `constitution.md` and `roadmap.md` to match the new code, fixing every mismatch listed in `view.md` §2.3. `progress.md` gets a new entry.
- Document the CSV import, how to reset the DB, and how to create the superuser.
- `view.md` stays as the historical review.

## 3. Non-goals

- Rebuilding crafting or inventory. Bag prices (ArcheMarket step 7c).
- Automatic upload: no watcher, no collector, no API token for scripts.
- Multi-user features: watchlist, profiles, registration, emailed password resets.
- Upload history or audit pages; deleting imported data from the UI.
- More than 14 days on the chart, and range buttons.
- ESLint, Prettier or a Python type checker. They can come as a separate follow-up.
- Switching to React.

## 4. Anti-goals (a failure even if it "works")

- Uploading the same file twice changes data or counts.
- Rows lost without being reported: every data line must show up in exactly one of inserted, updated, skipped or errors.
- An older scan overwriting a newer day.
- Anyone except a superuser being able to import.
- Weakened prod hardening: the secrets validator, docs off in prod, the Caddy headers and admin allowlist, non-root images.
- Frozen crafting or inventory code deleted, or reachable (built, routed, type-checked or holding tables).
- A messy structure: modules with different core file sets, tests that do not mirror the code, extra files without a stated reason.

## 5. Constraints (house rules that stay)

- `podman compose` locally, through the Makefile.
- Tests use a real Postgres (`app_test`), no DB mocks, with unique test data and no cleanup between tests.
- Naive UTC datetimes in the DB.
- One slowapi limiter singleton.
- All API routes under `/api`, admin at `/admin`.
- Code comments, docs and PR text in English, short.
- Work happens on a feature branch, never on `main`. Nothing gets pushed without the user's say-so.
- The user's pending deletions go into the first commit of that branch, after the delete list is confirmed. **That commit must also carry the fixes that keep CI green:** the bot workflow, compose services, infra tests and the frontend env step.

## 6. Decided by the user

- Accept all recommendations in `view.md` (§4.8 defaults where it gave one).
- Stay with Svelte.
- Freeze crafting and inventory; rebuild them later.
- Remove the watchlist and profiles.
- Lay the backend and frontend out by domain, with tests mirroring the code (§2.3).
- The server runs on Moscow time, which gives the timezone for `day_date` (§8 Q2).
- Materials first, graded items later (§8 Q6).

## 7. Calls made by Claude, mostly from the reviews (the user may overrule)

- Frozen code moves to `backend/frozen/` and `frontend/frozen/`, outside every built and tested tree (§2.2). This is a change from the first draft, which kept it in place.
- `items/` is merged into `market/` (§2.3). This is a change from the agreed layout, because no item endpoint is left.
- Registration, forgot-password, reset-password and verify are removed. `create-superuser` doubles as the password reset.
- Items are resolved in Python per item. Market rows are deduplicated by date.
- `avg_7d` and `avg_daily_volume` cover the 7 full days before today.
- `bigint` for money; 50 MB file cap; import rate limit 10/min; at most 100 errors listed, plus `error_count`.
- `/` redirects to `/market`; `/items` is dropped.
- The CSP `connect-src` fix, the e2e build argument, and an e2e stack seeded with the superuser only.
- The test DB is reset with `DROP SCHEMA`, and `make dev-reset` is added.
- E2E in CI through `docker compose` (GitHub runners have Docker, not Podman), non-blocking.
- No ESLint or Prettier in this round.

## 8. Answered questions

- **Q2. The game day.** The ArcheRage server runs on Moscow time (the user's answer). `captured_at` is epoch seconds, so it carries no timezone at all. `day_date` is therefore computed in **`Europe/Moscow`** (UTC+3 all year, no DST), kept as one constant in `market/` with a one-line reason.
  - Computing it in UTC would shift every row of a scan taken between 21:00 and 24:00 UTC (22:00–01:00 CET) one day back. Because the newest scan wins, those wrong rows would overwrite correct ones.
  - A two-scan check in game around Moscow midnight, at about 22:00 CET, is recommended but does not block this work.
  - A test must cover a scan at 21:30 UTC landing on the next Moscow date.
- **Q6. Graded items.** The user will track different kinds of items: **materials first, graded gear later**. This round supports single-grade items only.
  - A graded item that shows up early is not misfiled silently. A market row whose name belongs to an item with a different non-null `(item_type, item_grade)` becomes a row error (§2.5, the collision rule), with the reason "name already used by another grade".
  - `docs/roadmap.md` gets an entry: "Graded items: needs ArcheMarket to write `item_type`/`item_grade` in `listings.csv`, then key items on `(item_type, item_grade)` only".

## 9. Left to the builder

- How the inserted, updated and skipped counts are obtained (for example `RETURNING (xmax = 0)`), and the chunk size.
- Chart styling details, component splitting inside `lib/market/`, and test names.
- The order of commits, as long as each commit leaves the tests green.
