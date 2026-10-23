# Item icons come from Codex by item type and are never committed

Status: accepted (2026-10-23)

The bag, warehouse and chest grids show an icon on each tile. The game's item info for bag items has no icon path; it was seen only on auction-house rows. So the app cannot take icons from the ArcheBag files.

Instead the backend looks the icon up on archeagecodex.com (Codex) by item type: it reads the Codex item page, finds the icon there, fetches the PNG once and keeps it in a server-side cache volume. The API serves cached icons publicly, so `<img>` tags need no credentials. When an item has no icon, the tile shows its grade colour.

Game icons are game assets. They are never committed to this public repo, not even as test fixtures.

## Considered options

- **An `icon` column written by ArcheBag, fetched from Codex by icon file name.** Planned first and dropped: bag item info has no icon field. The column was removed by a migration.

## Consequences

- Codex gives no clean "not found": an unknown item is a 200 `ERROR!` page and an unknown PNG is a generic image. Both are remembered as missing, so Codex is not asked again.
- ArcheRage's own items (ids 8 000 000 and up) are not on Codex and always show grade colours.
- Codex fetches are limited per minute and in parallel; cache hits are not.
- Tests never call Codex.
- Icons are keyed by item type only, the same at every grade ([ADR-0007](0007-item-identity-is-type-and-grade.md)).
