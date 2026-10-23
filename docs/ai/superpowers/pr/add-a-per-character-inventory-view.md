---
title: Add a per-character inventory view
issue: none
verdict: ready
created: 2026-10-23
---

# Add a per-character inventory view

## What

The bag of every character can now be imported from the ArcheBag addon's `inventory.csv` and viewed on a new `/inventory` page:
- one tab per character;
- a 10-column tile grid laid out like the in-game bag;
- a Codex icon on each tile, or a pastel grade colour when there is no icon;
- the item's count;
- a dot marking what changed since the previous snapshot;
- a tooltip with the details, which also opens on keyboard focus.

All uploads now go through one `POST /api/import`. It routes each file by its header: `inventory.csv` is open to any signed-in user, and market files stay admin only.

## Why

The goal is crafting help, so the app first has to know what each character holds. The data is stored per user from the start, because every player will eventually have their own inventory.

- Spec: `docs/ai/superpowers/specs/2026-10-23-inventory-design.md`
- Plan: `docs/ai/superpowers/plans/2026-10-23-inventory.md`

No linked issue. This PR is **stacked on #17** (Google login). Retarget it to `main` once #17 is merged.

## How to test

1. Start a test Postgres:
   ```
   docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16-alpine
   ```
   Then run `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q`.

   Expected: `150 passed`. The new tests live in `tests/imports/` and `tests/inventory/` (parser, keep-two import, read API, icon cache with a faked Codex).
2. Run `cd frontend && npm test && npm run check`.

   Expected: 57 tests pass and svelte-check shows 0 errors.
3. Run e2e: `make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test`.

   Expected: 12/12, including `inventory.spec.ts`, which uploads `inventory.csv`, switches tabs and checks a tile's label.
4. Manual check: run `make dev-up`, sign in, and drop an `inventory.csv` from `Documents/Addon/archebag/` on `/import`. Then open `/inventory`.

## Risks

- **`POST /api/market/import` is gone** and is replaced by `POST /api/import`. The frontend, e2e and `seed.py` are updated. Any external script calling the old route breaks.
- **`/import` is open to every signed-in user.** Today every account is a superuser, so nothing changes in practice.
- **Icons come from archeagecodex.com.** Each icon is fetched once and cached in the `icon_cache` volume.
  - Codex answers unknown names with a generic image, which is detected by its hash.
  - Fetches are capped at 60 per minute per worker.
  - If Codex changes its URLs or its placeholder, tiles fall back to grade colours.
- **No icons yet.** ArcheBag does not write the `icon` column yet, so every tile is a grade colour until it does.
- **The backend image now creates `/app/icon-cache`,** and the dev and prod compose files mount the new `icon_cache` volume there.

## Rollback

Revert this PR and run `alembic downgrade 0001`, which drops the `inventory_slot` and `inventory_snapshot` tables. That takes about a minute. The uploaded bag snapshots are lost, and re-uploading `inventory.csv` restores them. Market data is untouched.

## Contract impact

- **API:**
  - New `POST /api/import`.
  - `POST /api/market/import` is removed.
  - New `GET /api/inventory/characters` and `GET /api/inventory/characters/{name}` (signed-in user's own data).
  - New public `GET /api/inventory/icons/{name}.png`.
  - `ImportFileResult.kind` gains `"inventory"`.
- **Database:** migration `0002_inventory` adds `inventory_snapshot` and `inventory_slot`.
- **CSV:**
  - Accepts the ArcheBag header `snapshot_id,captured_at,character,slot,item,item_type,item_grade,count`.
  - Also accepts the same header with a trailing `icon` column.
- **Config:** new `ICON_CACHE_DIR` (default `/app/icon-cache`) and the `icon_cache` compose volume. The CSP `img-src` gains the API origin.

---

## Deferred items

- [ ] Range-check `item_grade`, `count` and `item_type` in the inventory parser, so a value out of range is one row error instead of a whole-file DB error.
- [ ] `list_characters` should count filled slots in SQL instead of loading every slot.
- [ ] Bound the `.missing` marker files in the icon cache.
- [ ] Clean up the `mkstemp` temp file when an icon write fails.
- [ ] A local run without the cache dir gives a 500 on the first icon miss; create the dir or return a 404.
- [ ] Serve icons with `FileResponse` instead of sync reads in the async handler.
- [ ] Move `ApiError`, `getJson` and `uploadFiles` into `frontend/src/lib/core`.
- [ ] Add an inventory test that a DB error in one file does not block the next.
