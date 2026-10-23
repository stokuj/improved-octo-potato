# Items page: bag, warehouse and house chests — design

Status: draft for approval, 2026-10-23. Branch `feature/items`, from `main` at `26228cc` (PR #20 merged).

## Intent

The end goal is still help with crafting: the app must know everything the player owns, not only the bag. The ArcheBag addon (repo `ArcheMarket`, step 7d, retested in game 2026-10-23) now writes:
- the bag **and** the warehouse of a character to `inventory.csv`;
- house chests to a new `chests.csv`.

The app rejects both files today (`unknown header`). This step imports them and shows all three kinds of storage on one page.

Success:
- after uploading both files, the page shows each character's bag and warehouse, and every saved chest;
- every grid matches the game slot for slot, with the same tiles, icons, tooltips and change dots as today's bag;
- the user can look at one character and one chest, or at everything at once.

## Goals

1. Import the new `inventory.csv` (bag + warehouse) and `chests.csv` through the existing `/import` drop zone, mixed with other files.
2. Keep the newest and the previous snapshot **per place**:
   - a place is a character's bag, a character's warehouse, or a chest number;
   - change dots compare a place with its own previous snapshot.
3. Rename the page to **Items** at `/items`, laid out as below.

## Page layout (mockup E1 with "All", chosen by the user)

Mockups: `.superpowers/brainstorm/183378-1792762547/content/items-v4-e1-all.html` (not committed).

- The navbar link `Inventory` becomes `Items` and points to `/items`. `/inventory` redirects to `/items`, keeping `?character=`.
- The page is split into a **left** and a **right** column. On a narrow screen the right column drops below the left one.
- **Left: characters.** Tabs `All | <character>…`, characters sorted by name.
  - A character tab shows that character's **Bag** and **Warehouse** grids side by side. Each grid header shows `filled / slots` and that grid's own snapshot time and previous snapshot time, because bag and warehouse keep their history separately (for example right after the migration only the bag has a previous snapshot).
  - `All` lists every character one under another, each with its name and its Bag and Warehouse side by side, with the same grid headers.
  - A character that has only a bag (or only a warehouse) shows just that grid.
- **Right: house chests.** Tabs `All | <chest name>…`, ordered by chest number.
  - A chest tab shows that chest's grid with `filled / slots · saved by <character> <time>`.
  - `All` shows every chest side by side, wrapping to as many per row as fit.
  - A chest's label is its last non-empty name, or `Chest <number>` if it was never named.
  - With no chests saved, the right column says how to save one (`Chest` button in game, then upload `chests.csv`).
- The two tab sets are independent. The choice lives in the URL: `?character=<name>|All&chest=<number>|All`. Without a parameter, or with an unknown value, that side shows `All`.
- Every grid uses the existing 10-column (the in-game chest window is 10 wide too, screenshot `farmers-large-chest.png`) `InventoryGrid` and `InventoryTile` unchanged: icon over grade colour, count, tooltip, change dot, dashed empty slots.
- The empty state (no data at all) names both files and both in-game buttons (`Bag`, `Chest`).

**Changed after the first build (user, 2026-10-23):** from 1280px wide, each side shows two grids per row (bag and warehouse on the left, two chests on the right), 20 columns a side; tiles are fluid instead of a fixed 36px, and counts from 10 000 read as `10k`. Narrower screens stack the two sides.

**Changed again (user, 2026-10-23): bag chests go with their character.** A chest item in a character's bag (for example Adventurer's Chest) opens only from that bag, so the character who saved it owns it. Such a chest shows on the left after that character's bag and warehouse; the right keeps only house (land) chests. The file has no chest id, so the app matches names: a chest belongs to the character who saved it when that character's newest bag holds an item whose name starts with the chest's name (case, punctuation and the word "Chest" ignored, whole words only). Unnamed chests and chests with no matching bag item are house chests. This is computed in the frontend (`chestOwner` in `grid.ts`); the API is unchanged.

## Data contracts (ArcheBag step 7d, `ArcheMarket/llm-wiki/project/step7d-design.md`)

`inventory.csv`, exact header:

```
snapshot_id,captured_at,character,container,slot,item,item_type,item_grade,count,category,npc_price
```

- `container` is `bag` or `bank` (shown as Warehouse).
- One `Bag` click writes the bag, then the warehouse, under **one** `snapshot_id`; both are 150 slots in the retest.
- Empty slot: `item`, `item_type`, `item_grade`, `category`, `npc_price` empty, `count` 0 (as in 7c).

`chests.csv`, exact header:

```
snapshot_id,captured_at,character,chest,name,zone,x,y,z,slot,item,item_type,item_grade,count,category,npc_price
```

- `chest` is the number 1–10 the user picked; it is the chest's identity. `name` is free text, at most 15 characters, may be empty, and may change between saves.
- `character` is who saved it. Chests belong to the house, not to a character.
- Chest sizes seen: 30, 50, 100 slots.

Both files are append-only and keep the 7c rules: `captured_at` is epoch seconds, a same-second double click repeats a run starting at slot 1, and slots are `1..N` with no gaps.

## Decided by the user (2026-10-23)

- One page, **Items**, split left (characters) | right (chests). Mockup E1.
- **Warehouse is per character**: switching character switches both the bag and the warehouse.
- **Chests are shared**: they do not change when the character changes.
- Both sides have an **All** option; the user has a wide screen.
- Default without URL parameters: `All` on both sides.
- A chest is identified by its number; a new name in game renames it in the app.
- **An empty name means "no change"**: the chest keeps its last non-empty name. The addon may lose its name boxes after a game restart (ArcheMarket open question 14), and names must survive that. The name therefore outlives the two kept snapshots and is stored per `(user, chest)`. A name can't be cleared; a chest never named is `Chest <number>`.

## Non-goals

- Showing or storing `category`, `npc_price`, `zone`, `x`, `y`, `z`. They stay in the CSV for later steps (values, crafting).
- Search or a "where is this item" list (mockup C). A later step.
- Deleting a chest number the user no longer uses. It stays until it gets new snapshots.
- Guild bank, equipment, mail.
- Addon changes.

## Anti-goals

- A user sees another user's characters or chests.
- Real character names in this repo. Fixtures use made-up names (`Alpha`, `Bravo`); the retest files in `ArcheMarket` contain a real name and must not be copied as-is.
- Breaking the import invariants: re-upload is a no-op, the newest snapshot wins, `inserted + updated + skipped + error_count == rows` per file.

## Constraints

- Follow the existing `inventory` module: parser in `csv_format.py`, keep-two import in `services.py`, read API under `/api/inventory`, Alembic migration with `alembic check` clean.
- Inventory files stay open to any signed-in user (market files stay admin only).
- The same row and run checks as today: bad row → `{line, reason}`, a bad run rejects that whole snapshot, at most 300 slots.
- Existing stored bag snapshots become the bag of their character (migration).
- Frontend: Svelte 5 runes, DaisyUI, existing tile components; vitest tests for the page; regenerated `api.d.ts`.

## Calls I made (not discussed with the user)

- **The old 8-column `inventory.csv` header is no longer accepted.** The addon refuses to append to it, and the user deleted the old file in the 7d test. Test fixtures move to the new header.
- **Grouping:** `inventory.csv` lines are grouped by `(character, container, snapshot_id)`, `chests.csv` lines by `(chest, snapshot_id)`; within a group the last run wins, as today.
- **Chest metadata** shown in the app comes from its newest snapshot (slot count, saved-by character, time); the name follows the rule above.
- `ImportFileResult.kind` gains `"chests"`; the bag + warehouse file stays `"inventory"`.

## Left to the builder

- Table layout: extend `inventory_snapshot` with a container and a chest number, or add chest tables. Either way keys must keep re-upload idempotent and keep-two per place.
- Read API shape, as long as the `All + All` view needs only a handful of requests, not one per grid.
- Component split on the page and exact spacing.
- Test structure.
