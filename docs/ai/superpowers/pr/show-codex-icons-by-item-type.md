---
title: Show Codex icons by item type
issue: none
verdict: ready
created: 2026-10-23
---

# Show Codex icons by item type

## What

Bag tiles now show real item icons. The server looks each icon up on the ArcheAge Codex item page by `item_type`, which every `inventory.csv` row already has:
- it reads the first image in the page's `item-icon` cell;
- it fetches that PNG once and caches it as `{item_type}.png`.

The unused `icon` CSV column and the `inventory_slot.icon` column are removed.

## Why

The plan was for ArcheBag to write an `icon` column, but the game's item info for bag and warehouse items has no icon path, only `gradeIcon` (ArcheMarket invspike dump, 2026-10-23). The `icon` field exists only on auction rows. Looking the icon up by `item_type` needs no addon change.

No linked issue.

## How to test

1. Start a test Postgres:
   ```
   docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16-alpine
   ```
   Then run `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q`.

   Expected: `156 passed`. `tests/inventory/test_icons.py` covers:
   - the page parser, including subfolder icons and rejected paths;
   - the unknown-id `ERROR!` page and the placeholder PNG, both cached as missing;
   - a changed page layout and 5xx answers, which are not cached;
   - the fetch budget and the cap of 4 parallel fetches.
2. Run `cd frontend && npm test && npm run check`.

   Expected: 57 tests pass and svelte-check shows 0 errors.
3. Manual check: run `make dev-up` and `alembic upgrade head`, sign in, import `backend/tests/inventory/fixtures/inventory.csv`, then open `/inventory`.

   Expected:
   - most tiles show icons;
   - ArcheRage-only items (ids 8 000 000 and up) stay grade colours;
   - `curl -s -o /dev/null -w '%{http_code} %{size_download}' http://localhost:8000/api/inventory/icons/16327.png` prints `200 3625` (Leather).

## Risks

- **We parse Codex HTML.** If Codex changes its item page, icon misses are not cached. Each tile then retries until the 60-per-minute budget answers 503, and tiles show grade colours. Fixing it means updating `_ICON_CELL` / `_ICON_SRC` in `icons.py`.
- **Codex drops about 1 in 7 TCP connects.** Measured on 2026-10-23, also with curl. Each fetch retries connects twice with a 2 s connect timeout. After that, a failed icon is retried on the next page load.
- **Item ids come from the Codex `us` database.** They matched ArcheRage for every official item checked. ArcheRage's own items (8xxxxxx, 9xxxxxx) are not on Codex and stay grade colours.
- **The icon cache volume may hold name-keyed files** (`icon_item_0352.png`) from the previous scheme. They are harmless and never read.

## Rollback

Revert this PR and run `alembic downgrade 0002`. That re-adds `inventory_slot.icon` as a nullable column (empty) and takes about a minute. No data is lost: the column was always empty, because ArcheBag never wrote it.

## Contract impact

- **API:**
  - `GET /api/inventory/icons/{name}.png` becomes `GET /api/inventory/icons/{item_type}.png` (positive integer; anything else is 422).
  - `SlotRead.icon` is removed.
- **Database:** migration `0003_inventory_drop_icon` drops `inventory_slot.icon`.
- **CSV:** `inventory.csv` with a trailing `icon` column is no longer accepted (`unknown header`). No tool ever wrote it.
- The frontend is updated in the same PR; there are no other consumers.
