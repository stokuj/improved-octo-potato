# Architecture

## System overview

```
Player's PC                                   Server
───────────                                   ──────
ArcheRage + ArcheMarket addon                 Caddy (TLS, headers)
  └─ writes listings.csv, market.csv           ├─ /api/*   → FastAPI backend
ArcheBag addon                                 ├─ /admin*  → FastAPI (sqladmin, IP allowlist)
  └─ writes inventory.csv, chests.csv          └─ /*       → SvelteKit (adapter-node)
Browser
  └─ /import: drag & drop CSVs ──────────────► POST /api/import  (signed in; market files admin only)
  └─ /market: charts and tables  ◄──────────── GET  /api/market/*    (public)
  └─ /items: bag, warehouse, chests ◄──────── GET  /api/inventory/* (own data; icons public)
                                              PostgreSQL 16 · icon cache volume ◄── archeagecodex.com
```

Both addons live in a separate repo (`ArcheMarket`); their CSV contracts are described there (`llm-wiki/project/step7-design.md`, `step7b-design.md`, `step7c-design.md`, `step7d-design.md`). Nothing uploads automatically: the user uploads files by hand.

## Backend modules (`backend/app/`)

| Module | Holds |
|---|---|
| `core/` | settings (prod secret checks), DB engines/session, app errors, the single rate limiter, `utcnow()` |
| `admin/` | sqladmin setup; its auth backend accepts the app's auth cookie for superusers only |
| `auth/` | `User` model, fastapi-users wiring (cookie JWT), Google OAuth (`oauth.py`), password login outside prod, `/api/users/*`, `cli.py` (`create-superuser`) |
| `market/` | `Item`, `MarketDay`, `Listing`; CSV parsing (`csv_format.py`), import and read services, `/api/market/*` |
| `imports/` | `POST /api/import`: detects each file's kind by its exact header and hands it to `market` or `inventory`; `ImportFileResult` and `failed()` |
| `inventory/` | `InventorySnapshot`, `InventorySlot`, `ChestName`; `inventory.csv` and `chests.csv` parsing (`csv_format.py`), keep-two import per place, read API, Codex icon cache (`icons.py`), `/api/inventory/*` |

Frozen reference code (not imported, routed, migrated or tested): `backend/frozen/{crafting,inventory}`, `frontend/frozen/{crafting,inventory,e2e}`.

## Database schema

```
user        id uuid PK, email UNIQUE, hashed_password, is_active, is_superuser, is_verified
item        id PK, item_type int NULL, item_grade int NULL, name varchar(120), created_at
            UNIQUE (item_type, item_grade), UNIQUE (name)
market_day  PK (item_id → item.id, day date), daily_avg, weekly_avg, min, max, volume (bigint),
            scan_id bigint, captured_at timestamp
listing     PK (item_id → item.id, scan_id bigint, rank smallint), captured_at, status,
            unit_price bigint NULL, listing_price bigint NULL, stack int NULL
inventory_snapshot  id PK, user_id → user.id (CASCADE), container varchar(5) (bag|bank|chest),
                    chest smallint (1..10, 0 unless chest), character varchar(64) (for a chest: who saved it),
                    snapshot_id bigint, captured_at, slot_count
                    UNIQUE (user_id, container, chest, character, snapshot_id)
inventory_slot      PK (snapshot → inventory_snapshot.id CASCADE, slot), item NULL, item_type NULL,
                    item_grade NULL, count   (empty slots stored too)
inventory_chest_name  PK (user_id → user.id CASCADE, chest smallint), name varchar(15), captured_at
```

Migrations: `0001_baseline`, `0002_inventory`, `0003_inventory_drop_icon`, `0004_inventory_places` (existing snapshots become bags). Copper is stored as integers (1 g = 10 000 c). `item_grade` is the raw game int (`ITEM_GRADE_TYPE`, 0 for most materials).

## Import flow (`POST /api/import`)

`imports.services.import_file` reads the first line of each file:
- the inventory or chests header goes to `inventory`, with kind `inventory` or `chests`;
- a market or listings header goes to `market`, but only for a superuser. Anyone else gets that file back with one error, `admin only`;
- anything else goes to `market`, which answers `unknown header`.

The caller's `id` and `is_superuser` are read once, before the loop. A file that fails rolls back the shared session and expires the `User`.

### Market files

1. Each uploaded file (50 MB cap, rate limit 10/min) is parsed by `csv_format.parse_csv`:
   - the type comes from the exact header row;
   - quoted names follow RFC 4180;
   - a BOM and CRLF are accepted;
   - each row is validated, and a bad row becomes `{line, reason}` while the rest still imports.
2. Items are resolved by `(item_type, item_grade)` first, then by `name`. A name already owned by another grade is a row error.
3. **market.csv:** `day_date = date(captured_at in Moscow time) − (14 − day)`, because the server runs on UTC+3 and day 14 is today.
   - Rows are deduplicated in memory by `(item_id, day_date)`, and the newest `captured_at` wins.
   - They are then upserted with `ON CONFLICT … DO UPDATE … WHERE stored.captured_at < new.captured_at`.
4. **listings.csv:** bulk `INSERT … ON CONFLICT DO NOTHING`.
5. Each file is one transaction, written in chunks of 2 000 rows (asyncpg bind-param limit).

### Invariants

- **Idempotent:** re-uploading a file changes nothing (`inserted = updated = 0`).
- **Newest scan wins** per (item, date). An older scan never overwrites a newer one.
- **Sum rule:** per file, `inserted + updated + skipped + error_count == rows`. A whole-file failure (empty, not UTF-8, unknown header, too large, DB error) is one `errors` entry at line 0 with `error_count = rows`.
- At most 100 errors are listed; `error_count` is the total.

### Inventory files

1. `inventory/csv_format.parse_inventory` reads either header (the old 8-column one is `unknown header`) and groups lines by place and `snapshot_id`: `(container, character, snapshot_id)` for `inventory.csv`, where one `Bag` click writes the bag and the warehouse under one `snapshot_id`, and `(chest, snapshot_id)` for `chests.csv`. `category`, `npc_price` and the chest position are read past and not stored.
   - Inside a group, each `slot == 1` starts a new run, and only the last run is kept. A same-second double click in game writes two runs; the earlier ones count as `skipped`.
   - The kept run must have slots exactly `1..N` with N ≤ 300 and a single `captured_at`. Otherwise every line of it is an error.
2. For each place (a character's bag, a character's warehouse, or a chest number whoever saved it), the stored snapshots and the uploaded ones are ranked by `(captured_at, snapshot_id)` and only the **two newest** are kept.
   - Older snapshots are deleted, and their slots cascade.
   - A snapshot that is already stored, or that is too old to make the top two, is skipped.
   - The same sum rule applies.
3. **Chest names.** An empty name means "no change", because the addon's name boxes can come up empty after a game restart. Per chest, the newest named save in the file is upserted into `inventory_chest_name` when it is newer than the stored one, so an older file never renames a chest back.

## Inventory read API (`/api/inventory`, signed-in user's own data)

| Endpoint | Returns |
|---|---|
| `GET /characters` | the user's characters by name, each with `bag` and `bank` grids (or null) |
| `GET /chests` | the user's chests by number, each a grid plus `chest`, `name` (null if never named) and `saved_by` |
| `GET /icons/{item_type}.png` | a cached Codex icon; **public**, 404 when missing, 422 for a non-positive or non-integer id |

- **Grids.** A grid is a place's newest snapshot: `captured_at`, `previous_captured_at`, `slot_count`, `filled` and its slots in order. Each list loads with one query for snapshots and one for slots.
- **Change flags.** `change` compares totals per `(item_type, item_grade)` against the place's previous snapshot: `new`, `up`, `down`, or null when there is no change or no previous snapshot. A moved stack is no change, and items that left the bag are not shown.
- **Ownership.** Every query is scoped to the signed-in user; others' data never appears.
- **Icons.**
  - The game gives no icon path for bag items, so icons are looked up by `item_type`. A cache miss fetches the Codex item page `https://archeagecodex.com/us/item/{item_type}/`, takes the first image in its `item-icon` cell (`items/…png`, sometimes in a subfolder; a Windows `\` separator in the path is read as `/`), then fetches that PNG (5 s timeout) into `ICON_CACHE_DIR/{item_type}.png`.
  - Codex answers an unknown id with a 200 `ERROR!` page, and an unknown PNG with a generic image recognised by its SHA-256. Both are remembered as `{item_type}.missing`, and so is an icon cell whose path is not a Codex `items/…png`; the tile shows its grade colour.
  - A page without the icon cell (Codex changed its HTML), a non-200 or a network error is not cached and is retried on the next request.
  - Codex drops about 1 in 7 TCP connects, so each fetch retries connects twice (2 s connect timeout), and at most 4 fetches run in parallel.
  - ArcheRage's own items (ids 8 000 000 and up) are not on Codex, so they stay grade colours.
  - At most 60 Codex fetches per minute per process; over that, the answer is 503. Cache hits are not limited.

## Read API (`/api/market`, public)

| Endpoint | Returns |
|---|---|
| `GET /items` | items with any data, plus `last_day` |
| `GET /items/{id}/days?days=14` | the last N days, oldest first |
| `GET /items/{id}/listings` | the newest scan's rows, by rank |
| `GET /summary` | one row per item with market data |

How `/summary` is computed. "Today" is the item's newest day:
- `avg_7d` is the `weekly_avg` of the day before today. The game's weekly average includes the day itself, so this keeps the partial day out.
- `change_pct = (today_avg − avg_7d) / avg_7d`.
- `avg_daily_volume` is the mean volume of the 7 days before today.

## Auth

- Single-user app: there are no register, forgot, reset or verify routes.
- The admin is created, or has its password reset, with `python -m app.auth.cli create-superuser EMAIL PASSWORD` (`make create-superuser`).
- Cookie JWT (`fastapiusersauth`) lasts 7 days.
- **Production signs in with Google only.** The password route `POST /api/auth/login` (5/min) is mounted only when `ENVIRONMENT != prod`, for dev and e2e. `POST /api/auth/logout` exists everywhere.
- Google flow:
  1. `/auth` calls `GET /api/auth/google/authorize`; the backend returns the consent URL and sets a CSRF cookie.
  2. Google redirects the browser to `{FRONTEND_URL}/auth/callback?code&state`.
  3. That page calls `GET /api/auth/google/callback` with the query; the backend checks state + CSRF, exchanges the code and reads the **verified primary** email (`VerifiedGoogleOAuth2`).
  4. `UserManager.oauth_callback` signs in only an existing active superuser with that email (case-insensitive). It never creates users and stores no OAuth accounts or tokens.
- The Google router is mounted only when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set; prod refuses to start without them.
- `/admin` reads the same cookie; anyone else is redirected to `{FRONTEND_URL}/auth`. `/admin/login` redirects there too, so sqladmin's password form never shows.
- Google errors reach the frontend as fixed codes: `LOGIN_BAD_CREDENTIALS`, `OAUTH_NOT_AVAILABLE_EMAIL` (unverified email), `GOOGLE_PROFILE_UNAVAILABLE` (People API call failed), `OAUTH_CODE_EXCHANGE_FAILED` (reused code or bad client secret; Google's text goes only to the log), `access_denied` (consent cancelled).
- The API cannot change a user's email (`UserUpdate` has no `email`): in prod it is the Google sign-in key.
- `UserRead` exposes `is_superuser` so the frontend can show `/import`.

## Frontend (`frontend/src/`)

| Path | Holds |
|---|---|
| `lib/core/` | API base URL, auth state (Svelte 5 runes + context), `formatCurrency`, generated `api.d.ts` + `types.ts` |
| `lib/market/` | API helpers, `chart.ts` (pure ECharts option builder), `MarketChart`, `ListingsTable`, `SummaryTable`, `ImportDropzone` |
| `lib/inventory/` | API helpers, `grid.ts` (slot position, tile label, change dot, `pickTab`, `chestLabel`, `chestOwner`, `snapshotTime`), `grades.ts` (grade names, pastel placeholder colours and in-game frame colours), `GridPanel`, `InventoryGrid`, `InventoryTile` |
| `routes/` | `/` → `/market`, `/market`, `/items` (characters left, each with the chests in their bag; house chests right; `?character=` and `?chest=`, `All` by default), `/inventory` → `/items`, `/import` (signed in), `/auth` (Google button; password form when `PUBLIC_PASSWORD_LOGIN=true`), `/auth/callback`, `/about` |

- The chart is one ECharts instance with two stacked panels sharing the date axis: daily and 7-day average lines on top, volume bars below. It uses the SVG renderer.
- CSP `connect-src` and `img-src` allow the origin of `PUBLIC_API_URL`, set in `svelte.config.js`. Icons are served by the API.
- **Every grid** (bag, warehouse, chest) is 10 columns, with slot 1 top-left, inside a `GridPanel` that shows `filled / slots` and its own snapshot times.
  - A tile shows the Codex icon over its grade's pastel colour, which is all that shows when the icon is missing or fails to load.
  - A filled tile is square with a 2px frame in its grade's in-game colour (sampled from Codex `images/icon_grade{n}.png`; grade 0 uses Basic's white). Grades 8 and up have ornate frames in game, drawn here as a light-dark-light gradient.
  - Empty slots have a dashed outline.
  - The count sits bottom-right, and a change dot top-left.
  - The tooltip and the `aria-label` carry the name, grade, count and delta.
