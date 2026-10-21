---
title: Rebuild price data on ArcheMarket CSV uploads
issue: none
verdict: ready
created: 2026-10-21
---

# Rebuild price data on ArcheMarket CSV uploads

## What
- The dead JSONL/Discord-bot price pipeline is replaced by manual uploads of the ArcheMarket addon's `market.csv` and `listings.csv` on `/import` (admin only). They are stored idempotently.
- A new `/market` page shows, per item, a 14-day chart (daily and 7-day average, plus volume), the cheapest current offers, and a today-vs-7-days table for all items.
- The repo is reorganised by domain:
  - backend `core/`, `admin/`, `auth/`, `market/`, with tests mirroring them;
  - frontend `lib/core`, `lib/market`;
  - e2e moved into `frontend/e2e`;
  - a single env template in `infra/`.
- The bot, old addons, ingest, prices, watchlist and profiles are removed. Crafting and inventory are frozen as reference code for a later rebuild.

## Why
- Prices no longer arrive through the old addon, watcher or bot.
- The new source is the ArcheMarket addon's CSV output, which the user uploads by hand.

Design and decisions: `docs/ai/superpowers/specs/2026-10-21-archemarket-csv-design.md`. Stage-1 review: `docs/ai/view.md`. Plan: `docs/ai/superpowers/plans/2026-10-21-archemarket-csv.md`.

## How to test
1. Backend (Postgres with an `app_test` database):

   ```
   cd backend && uv run ruff check . && uv run pytest
   ```

   Expect 74 passed. The import tests use the real samples:
   - `market.csv`: 406 rows, 140 inserted, 266 skipped;
   - `listings.csv`: 250 rows, all inserted;
   - a re-upload inserts nothing.
2. Frontend:

   ```
   cd frontend && npm ci && echo "PUBLIC_API_URL=http://localhost:8000/api" > .env && npm run check && npm test
   ```

   Expect 0 svelte-check errors and 33 passed tests.
3. E2E:

   ```
   make e2e-up && make e2e-seed && make e2e-test
   ```

   Expect 10 passed: login, import, re-upload, `/market` chart and tables, item switch, anonymous read-only. The CI job is non-blocking for now.
4. Manual check:
   - `make dev-reset && make create-superuser EMAIL=me@example.com PASSWORD=...`;
   - sign in, open `/import`, drop both CSVs from `backend/tests/market/fixtures/`, then drop them again: the second run shows 0 inserted and 0 updated;
   - open `/market` and switch items.

## Risks
- **Database reset required.** All old migrations are replaced by one baseline (`0001_baseline`), so existing dev/e2e/prod volumes must be dropped. Old price data is not migrated.
- **Frontend dependencies.** The dependabot bump on `main` (`611be11`, SvelteKit 3 / vitest 5 / adapter-node 6) does not install (ERESOLVE) and needs a framework migration. This PR goes back to SvelteKit 2.70.3 and applies audit fixes within those majors. 3 low-severity advisories remain (cookie via kit 2, fixed only in kit 3). Expect dependabot to reopen those majors.
- **Account flows.** Registration and password reset are removed. Accounts come only from `python -m app.auth.cli create-superuser` (`make create-superuser`).
- **Game day timezone.** The market "game day" is computed at UTC+3 (the server's Moscow clock). This has not yet been verified in game around Moscow midnight.
- **Not run in this environment:**
  - `make dev-up` (no podman; compose validated with `docker compose config`);
  - the new CI workflows;
  - the e2e suite after the last `/market` fix. Vitest covers that fix, and the e2e suite passed 10/10 just before it.

## Rollback
Revert this PR. Old data cannot be restored from the new schema, so a revert also needs a DB volume reset followed by the old migrations (`alembic upgrade head` on an empty DB, about 1 minute). No production data is converted in either direction.

## Contract impact
- **API removed:**
  - `POST /api/ingest/prices`;
  - `GET /api/items/*`, `GET /api/items/{id}/price-history`, `POST /api/items/{id}/prices`;
  - `/api/user-items/*`, `/api/profiles/*`, `/api/crafting/*`, `/api/inventory/*`, `/api/me`;
  - `/api/auth/{register,forgot-password,reset-password,request-verify-token,verify}`.
- **API added:** `POST /api/market/import`, and `GET /api/market/{items,items/{id}/days,items/{id}/listings,summary}`.
- **API changed:** `UserRead` now includes `is_superuser`.
- **DB schema:** new baseline with `user`, `item(item_type, item_grade, name)`, `market_day`, `listing`. The `pricepoint`, `useritem`, `profile`, `recipe*` and `userinventory` tables are gone.
- **Config:** `INGEST_TOKEN` and `DISCORD_*` removed. The env template moved to `infra/.env.example`, and the Makefile passes `--env-file infra/.env` when that file exists.
- **Consumers:** the Discord bot (removed here) was the only external consumer. Nothing else is known to depend on the removed endpoints.

### Follow-ups (deferred from review)
- [ ] The "name already used by another grade" message is misleading when the clash is with a listing-only item.
- [ ] When `PUBLIC_API_URL` is unset in a prod build, `localhost:8000` ends up in the CSP `connect-src`.
- [ ] Add a Caddy `request_body max_size` as the real upload cap. Starlette spools the whole multipart body before the 50 MB check.
- [ ] Add a last-resort `except Exception` in `import_csv` as a safety net.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
