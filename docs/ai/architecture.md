# Architecture

## System overview

```
Player's PC                                   Server
───────────                                   ──────
ArcheRage + ArcheMarket addon                 Caddy (TLS, headers)
  └─ writes listings.csv, market.csv           ├─ /api/*   → FastAPI backend
                                               ├─ /admin*  → FastAPI (sqladmin, IP allowlist)
Browser                                        └─ /*       → SvelteKit (adapter-node)
  └─ /import: drag & drop both CSVs ─────────► POST /api/market/import (superuser)
  └─ /market: charts and tables  ◄──────────── GET  /api/market/*      (public)
                                              PostgreSQL 16
```

The addon is a separate repo (`ArcheMarket`); its CSV contract is described there (`llm-wiki/project/step7-design.md`, `step7b-design.md`). Nothing uploads automatically: the user uploads files by hand.

## Backend modules (`backend/app/`)

| Module | Holds |
|---|---|
| `core/` | settings (prod secret checks), DB engines/session, app errors, the single rate limiter, `utcnow()` |
| `admin/` | sqladmin setup; its auth backend accepts the app's auth cookie for superusers only |
| `auth/` | `User` model, fastapi-users wiring (cookie JWT), Google OAuth (`oauth.py`), password login outside prod, `/api/users/*`, `cli.py` (`create-superuser`) |
| `market/` | `Item`, `MarketDay`, `Listing`; CSV parsing (`csv_format.py`), import and read services, `/api/market/*` |

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
```

One Alembic baseline (`0001_baseline`). Copper is stored as integers (1 g = 10 000 c). `item_grade` is the raw game int (`ITEM_GRADE_TYPE`, 0 for most materials).

## Import flow (`POST /api/market/import`)

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
| `routes/` | `/` → `/market`, `/market`, `/import`, `/auth` (Google button; password form when `PUBLIC_PASSWORD_LOGIN=true`), `/auth/callback`, `/about` |

- The chart is one ECharts instance with two stacked panels sharing the date axis: daily and 7-day average lines on top, volume bars below. It uses the SVG renderer.
- CSP `connect-src` allows the origin of `PUBLIC_API_URL`, set in `svelte.config.js`.
