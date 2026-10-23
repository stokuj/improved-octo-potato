---
title: Show bag, warehouse and house chests on an Items page
issue: none
verdict: ready
created: 2026-10-23
---

# Show bag, warehouse and house chests on an Items page

## What
Imports the ArcheBag 7d files: `inventory.csv` with bag and warehouse, and the new `chests.csv` with house chests. They show on a new **Items** page (`/items`; `/inventory` redirects there).
- **Left:** each character's bag, warehouse and the chests kept in that character's bag.
- **Right:** the house (land) chests.

Both sides have `All | name` tabs kept in the URL. From 1280px each side is 20 columns wide.

## Why
Crafting help needs to know everything the player owns, not only the bag. The app rejected both new addon files (`unknown header`).

No issue.

## How to test
1. Backend: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest`. Expected: 180 passed. Then `uv run ruff check . && uv run ruff format --check .`.
2. Migration: `uv run alembic upgrade head && uv run alembic check`, then `alembic downgrade -1` and `upgrade head` again. Existing bag snapshots become `container='bag'`. The downgrade drops warehouse and chest snapshots.
3. Frontend: `cd frontend && npx vitest run && npm run check`. Expected: 69 passed, 0 errors.
4. e2e: `make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test`. Expected: 13 passed.
5. By hand:
   - Upload `backend/tests/inventory/fixtures/inventory.csv` and `chests.csv` on `/import`.
   - Open `/items`: Alpha and Bravo show their bags, Alpha its warehouse, and the chests Treehouse and Chest 2 are on the right.
   - Switching a tab on one side leaves the other side as it was.

## Risks
- **Bag chest vs land chest is a name match.** The CSV has no chest id. A chest goes under the character who saved it when that character's bag holds an item whose name starts with the chest's name (case, punctuation and the word "Chest" ignored). A land chest named after a bag item, or a chest number reused while it keeps its old name, shows on the wrong side. It is display only; no data is affected.
- **The old 8-column `inventory.csv` header is no longer accepted.** The addon no longer writes it.
- Only per-user data is read. Both read endpoints have tests that a user sees only their own data.

## Rollback
1. Revert this PR.
2. Run `alembic downgrade 0003` (seconds). The downgrade deletes warehouse and chest snapshots and drops `inventory_chest_name`. Bag snapshots stay.

## Contract impact
- **DB schema (migration 0004):**
  - `inventory_snapshot` gets `container` (`bag`/`bank`/`chest`) and `chest` (smallint).
  - The unique key becomes `(user_id, container, chest, character, snapshot_id)`.
  - New table `inventory_chest_name`.
- **API:**
  - Removed: `GET /api/inventory/characters/{character}` (only the old page used it).
  - Added: `GET /api/inventory/characters` (bag and warehouse grids) and `GET /api/inventory/chests`.
  - `ImportFileResult.kind` gains `"chests"`.
- **Import format:** accepts the ArcheBag 7d headers only (contract: ArcheMarket `llm-wiki/project/step7d-design.md`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## Deferred items

- [ ] A snapshot is cut short if its last line has a bad grouping key
- [ ] architecture.md misses the chest-names query
- [ ] Tests: non-superuser chests import; one chest saved by two characters in the same second
- [ ] Character and chest names sort by code point
- [ ] Tabs: ~300 tab stops per character, no arrow keys, no tabpanel ARIA; URL keeps a stale param
- [ ] Two `# type: ignore` in imports/inventory services (annotate `_INVENTORY_KINDS`; build `ChestRead` from a `GridRead`)
