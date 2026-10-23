# Gotchas

Problems hit while building this app that the code does not explain by itself. The ones that bite every session are in `CLAUDE.md`; this file holds the rest.

## Postgres and the import

- `ON CONFLICT DO UPDATE` refuses to touch the same row twice in one statement. That is why market days are deduplicated in memory before the upsert, not just for speed.
- Inserts and updates are told apart with `RETURNING (xmax = 0)`: a fresh row has `xmax = 0`.
- The game's `weekly_avg` includes the day itself, so today's partial day leaks into it. The 7-day average in `/summary` is the `weekly_avg` of the day before today.

## ArcheBag files

- A double click on **Bag** in the same second writes two runs of slots under one `snapshot_id`. Each `slot == 1` starts a new run; only the last run is kept.
- The addon's chest name box can come up empty after a game restart, so an empty name means "no change", never "rename to nothing".
- Bag and warehouse item info has no `icon` field (only `gradeIcon`). An icon path was seen only on auction-house rows, so icons are looked up on Codex by `item_type`.
- `npc_price` is probably copper; that is not verified.
- The raw addon files contain a real character name. Never copy one into the repo, not even inside a command you run to check something: the history had to be rewritten once.

## Codex icons

- An unknown item id gets a 200 page that says `ERROR!`, and an unknown PNG gets a generic image (recognised by its SHA-256). Both mean "missing", not a failure.
- Codex drops about 1 in 7 TCP connects. Connects are retried; without that, every page view loses icons.
- Some Codex pages keep the game's `\` in the icon path (`costume_bo\nu_f_bo_leather295.png`). With `/` instead, Codex serves the real icon.
- ArcheRage's own items (ids 8 000 000 and up) are not on Codex at all.
- A few Codex icons are simply wrong for the item. Not fixed yet.

## Frontend

- `+layout.svelte` sets `data-theme="night"`, but `layout.css` loads DaisyUI with its default themes only, so `night` does nothing and the app renders the **light** theme. Mockups and screenshots must use the light colours.

## Infra

- Caddy site addresses need `{$VAR}`, which is read when the config is parsed. `{env.VAR}` there fails `caddy validate`; it only works inside directives.

## Git and PRs

- A PR stacked on another branch merges into that branch, not into `main`. Retarget it to `main` before its base merges, or it misses `main` (PR #18 had to be reopened as #19).
