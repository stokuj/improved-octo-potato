---
title: Fix Codex backslash icons and frame tiles by grade
issue: none
verdict: ready
created: 2026-10-23
---

# Fix Codex backslash icons and frame tiles by grade

## What
- Codex icon paths that keep the game's Windows separator (`costume_bo\nu_f_bo_leather295.png`) are now read with `/`, so those items get their real icon.
- An icon cell whose path is still unusable is cached as `{item_type}.missing` instead of being refetched.
- Filled tiles on `/items` are square, with a 2px frame in the item's in-game grade colour. Grades 8 to 12 have ornate frames in game; here they are drawn as gradients.

## Why
- The old code treated an unusable icon path as a temporary error and cached nothing. As a result, every `/items` view asked Codex again for each such item, which risks a ban as these items add up. In the dev data three items were affected: Disciple's Brawler Boots and two +18 Sacred Hiram pieces.
- The user asked for grade frames like the game's bag and chest windows.

No issue.

## How to test
1. Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q` from `backend/`. Expected: 182 passed, including `test_icon_path_with_a_windows_separator` and `test_fetch_codex_unusable_icon_path_is_missing`.
2. Run `npm test && npm run check` from `frontend/`. Expected: 70 passed and 0 svelte-check errors. The new `grades.test.ts` case checks the frame colours.
3. On the dev stack, request `curl -o /dev/null -w '%{http_code} %{time_total}\n' localhost:8000/api/inventory/icons/47047.png` twice. Expected: `200` both times; the first takes about 0.2 s (Codex), the second about 2 ms (disk cache).
4. Open `/items` and compare a chest with the game. Expected: grade 0 and 1 are white, 2 green, 3 blue, 4 purple, 5 yellow, 6 orange, 7 red, and 8 to 12 show gradients.

Also run: ruff, `uv lock --check`, alembic up/check/down/up, e2e 13/13.

## Risks
- If Codex starts using an icon path format we don't parse, those icons are cached as missing for good, not retried. The tile shows its grade colour. Fix: delete the `*.missing` files from the `icon_cache` volume.
- Filled tiles lose their rounded corners; empty slots stay dashed and rounded.

## Rollback
Revert this PR; there are no migrations or data changes. Optionally delete `*.missing` files written after deploy from the `icon_cache` volume so they are fetched again.

## Contract impact
None. The `/api/inventory/icons/{item_type}.png` route keeps its responses (200 PNG, 404, 503); only which items return 200 changes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## Deferred items

- [ ] The pastel placeholder colours in `grades.ts` don't match the new frame colours. For example, grade 4 is a yellow fill inside a purple frame, which shows on ArcheRage-only items with no icon.
- [ ] Item counts like "2000" still touch the next tile at 1400px with 20 columns (as before this PR).
