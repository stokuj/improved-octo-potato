# Inventory (bag) view — design

Status: draft for approval, 2026-10-23. Branch `feature/inventory`, stacked on `feature/google-login` (PR #17, not merged yet). Rebase onto `main` once #17 is merged.

## Intent

The end goal is help with crafting. To do that, the app must know which items each of the player's characters actually holds. This step covers the **bag** only:
- the user exports it in game with the ArcheBag addon (separate repo `ArcheMarket`, step 7c);
- uploads `inventory.csv` on `/import`;
- sees each character's bag drawn like the in-game grid.

Warehouse, house chests and a search across all storage come in later steps.

Success:
- after an upload, `/inventory` shows every character of the signed-in user;
- each character's bag is laid out slot for slot as in game;
- every tile shows its item and count;
- each tile shows what changed since the previous snapshot.

## Goals

- Import `inventory.csv` through the existing `/import` drop zone. Several files can be dropped at once, mixed with `market.csv` / `listings.csv`.
- Store the **newest and the previous snapshot per character**, owned by the user who uploaded them.
- A new `/inventory` page with one tab per character and a 10-column grid of square tiles. A tooltip shows the details.
- Item icons from ArcheAge Codex, fetched once and cached by the backend. Without an icon, a tile is a pastel square in the colour of the item's grade.

## Non-goals

- Warehouse, house chests, equipped gear.
- Prices or values on tiles.
- Crafting.
- Search.
- Self-registration or a player role. Accounts still come only from `create-superuser`. The admin is a user like any other and owns their own inventory. Registration is a later stage.
- Full snapshot history. Only the two newest are stored.
- Changes to the ArcheBag addon. The `icon` column below is requested from that repo, not built here.

## Anti-goals

- **A user sees another user's characters or items.** Every inventory query is scoped to the signed-in user.
- **Real character names in this public repo.** Test fixtures use made-up names.
- **Icon fetching that hammers Codex or lets a request reach an arbitrary URL.** Each icon name is fetched at most once, and names are validated.
- **Committing game icons to the repo.**

## Decided by the user (2026-10-23)

- **Bag only for now.** Warehouse and chests come later.
- **One person, one game account, several characters.** The file holds all of them, told apart by the `character` column.
- **Page layout:** character tabs above the grid, with details in a tooltip, not a side panel. This is mockup option A, with B's tooltip.
- **Tiles** are too small for text. Each tile is an icon, or a pastel grade-coloured square, plus the count.
- **Icons** come from ArcheAge Codex, cached by the app.
- **History:** newest plus previous snapshot.
- **No prices** on tiles yet.
- **Upload:** the same `/import` drop zone, with several files at once.
- **Data is per user from the start.** "The admin is also a user."

## Data contract (from ArcheBag, step 7c, tested in game 2026-10-23)

`inventory.csv` is append-only. Its header is written once:

```
snapshot_id,captured_at,character,slot,item,item_type,item_grade,count
```

| Column | Value |
|---|---|
| `snapshot_id` | Epoch seconds of the click. The same for every line of one snapshot. |
| `captured_at` | Epoch seconds of the click. |
| `character` | Character name (`UnitName("player")`), RFC 4180 quoted when needed. |
| `slot` | `1..Capacity()`. One line per slot, in order, **empty slots included**. |
| `item` | Item name; empty for an empty slot. |
| `item_type` | Integer id; empty for an empty slot. |
| `item_grade` | Integer 0..12; empty for an empty slot. |
| `count` | Stack size; `0` for an empty slot. |

**Grid facts:**
- The grid is 10 columns wide and slot 1 is the top-left cell. Slot `s` sits at row `floor((s-1)/10)+1`, column `(s-1)%10+1`.
- Bag sizes seen in game: 90 and 150.
- Two clicks in the same second share a `snapshot_id`. The addon accepts this.

**Future `icon` column.**
- ArcheBag will be asked to append a ninth column, `icon`, after `count`.
- The game's item info carries `icon = "Game/ui/icon/icon_item_0352.dds"`, seen on AH rows. The column holds that value.
- The app accepts **both headers**. It normalises `icon` to the file's base name without extension (`icon_item_0352`), and an empty `icon` means no icon.
- Until the addon writes it, every tile uses the pastel placeholder.

A real two-character sample lives in the ArcheMarket repo at `llm-wiki/sources/raw/ingame/2026-10-23-step7c/inventory.csv`. It holds real character names. Fixtures here must be copies with the names replaced.

## How it works

### Import

- **One endpoint for all CSVs.** `POST /api/import` takes the multipart files, detects each file's kind from its exact header (`listings`, `market`, `inventory`) and hands it to that module's service. `/import` posts here.
  - **My call:** one endpoint, because the drop zone takes mixed files and the header is already the detection rule.
  - It is a thin router, in its own small module or in `core`, with a reason comment. It talks only to module services.
  - `POST /api/market/import` goes away. The `ImportFileResult` shape and its invariant stay the same, and `kind` gains `"inventory"`.
- **Who may upload what.** Any signed-in **active** user may upload `inventory.csv`. Use `fastapi_users.current_user(active=True)`; today's `current_user` does not check `is_active`. `market.csv` and `listings.csv` stay **superuser only**.
  - A non-superuser's market file comes back as that file's result with one error, `admin only`, while their inventory files still import.
  - The endpoint itself requires a signed-in user. Rate limit and 50 MB per-file cap as today.
  - **Today every account is a superuser**, because `create-superuser` is the only way in and Google sign-in admits only superusers. The non-superuser path is therefore reachable only in tests (`make_user`) until player registration exists. That is intended: the user chose "only me now, players later" with per-user data from the start. This step does not change auth.
  - `backend/seed.py` calls `app.market.services.import_csv` directly and must keep working.
- **Parsing.**
  - Same rules as the market parser: BOM, CRLF, exact header, a bad row becomes `{line, reason}`.
  - Lines are grouped by `(character, snapshot_id)`.
  - A snapshot is **valid** only if its slots are exactly `1..N` with no gap or duplicate, all lines carry the same `captured_at`, and N ≤ 300. **My call:** an upper bound against garbage.
  - Every line of an invalid snapshot becomes an error, because a partial bag would draw wrong.
- **Storing.** For each `(user, character)`, the uploaded valid snapshots and the stored ones are merged, and only the **two with the newest `captured_at`** are kept, older ones deleted. The ordering tie-break is `snapshot_id`.
  - A snapshot already stored is a no-op, so re-upload changes nothing. One that is too old to make the top two is skipped.
  - Accounting: for each file, `rows` counts its data lines.
    - `inserted` counts the lines of the snapshots stored by this upload.
    - `skipped` counts the lines of snapshots already stored or too old.
    - `updated` is always 0.
    - The invariant `inserted + updated + skipped + error_count == rows` holds.
  - One transaction per file, like the market import.
- **Identity.** A character is identified by its name within one user. The same name under two users is two different characters.

### Data model (`inventory` module: `models.py`, `schemas.py`, `services.py`, `router.py`)

**No sqladmin view (my call).** It would let a superuser browse every user's bag, which breaks the per-user anti-goal.


- `InventorySnapshot`:
  - columns: `id`, `user_id` (FK user, cascade delete), `character`, `snapshot_id` (bigint epoch), `captured_at` (naive UTC), `slot_count`;
  - UNIQUE `(user_id, character, snapshot_id)`.
- `InventorySlot`:
  - columns: `snapshot` (FK, cascade), `slot`, `item` (nullable), `item_type` (nullable), `item_grade` (nullable), `count`, `icon` (nullable);
  - PK `(snapshot, slot)`.
  - **Empty slots are stored too.** **My call:** the grid needs its exact size, and storing them keeps reads trivial.
  - Item fields live on the slot: there is no foreign key to `market.Item`. The market's `UNIQUE(name)` rule and graded gear (grades up to 12 seen in bags) do not fit together yet. Joining on `(item_type, item_grade)` comes with prices or crafting.
- An Alembic migration is required, and `alembic check` must stay clean.

### Read API (signed-in user, own data only)

- `GET /api/inventory/characters` lists the user's characters. Each entry has the name and, for the newest snapshot, `captured_at`, `slot_count` and the number of filled slots. Its `previous_captured_at` is null when there is only one snapshot. The list is sorted by name.
- `GET /api/inventory/characters/{character}` returns the newest snapshot's slots in order. Each slot has `slot`, `item`, `item_type`, `item_grade`, `count`, `icon` and `change`, plus the snapshot times.
  - `change` compares **per item**, keyed by `(item_type, item_grade)`. It sums the counts over all slots in the newest snapshot and in the previous one.
  - It is set on every filled slot of that item:
    - `"new"` when the item is absent from the previous snapshot;
    - `"up"` / `"down"` when the total grew or shrank;
    - null when the total is unchanged or there is no previous snapshot.
  - Moving a stack to another slot is not a change.
  - Items that left the bag completely are **not shown** (user, 2026-10-23). Only tiles still in the newest snapshot carry a change.
  - The tooltip also shows the delta, so the response carries `delta` (total now − total before) next to `change`.
  - 404 for an unknown character, which includes another user's character.

### Icons

- `GET /api/inventory/icons/{name}.png` serves a cached PNG.
  - On a cache miss the backend fetches `https://archeagecodex.com/items/{name}.png` once, with a short timeout. It stores the file in an icon cache directory, which is a compose volume and is git-ignored.
  - **Codex never answers 404.** Checked 2026-10-23: an unknown name gets `200 image/png` with one generic placeholder image (1891 bytes, identical for any unknown name), while a real name gets its icon. The backend therefore recognises that placeholder by its SHA-256 and treats it as **missing**. It then answers 404, so the frontend shows the pastel square, as the user wants for items without an icon.
  - A missing name is remembered (a marker), so it is not fetched again. The builder records the placeholder hash as a constant, taken from a real fetch, with a comment saying where it came from.
- **Validation.** Normalised names are lowercase, because game paths and Codex files are (`icon_item_0352`) and Codex is case-sensitive. `name` must match `^[a-z0-9_]{1,64}$`, anything else is 404. The URL is built only from the validated name, so it can't be used to fetch arbitrary pages (no SSRF).
- **Access.** Public read, with no user data in it. It is rate-limited, because a burst of misses turns into a burst of outbound fetches.
  - **My call:** public, so `<img>` tags need no credentials.
  - **The limit counts only Codex fetches (misses), not cache hits.** A 150-slot bag loads up to 150 icons at once, so a plain per-route limit would turn tiles pastel with 429s.
- **Fallback.** On any error the frontend falls back to the pastel square (`onerror`).
- The CSP `img-src` gains the API origin, because dev and e2e serve the API cross-origin.

### Frontend

- **Nav.** "Inventory" appears for signed-in users. `/import` opens to any signed-in user; its copy lists the three files and says market files are admin only.
- **`/inventory`.**
  - Tabs, one per character, labelled `name · slot_count`. The selected tab is kept in `?character=`, like `?item=` on `/market`.
  - Beside the tabs: the newest and previous snapshot time, in local time.
  - Below them the 10-column grid, with one square tile per slot:
    - an empty slot is a dark square;
    - a filled slot shows the icon, or the pastel square in its grade's colour;
    - the count sits bottom-right when it is above 1;
    - a small dot in a corner marks `change`: green up, red down, blue new.
  - The hover or focus tooltip shows the full name, the grade name and number, the count, and the delta from the previous snapshot.
- **Grade names and placeholder colours, 0..12:** None, Basic, Grand, Rare, Arcane, Heroic, Unique, Celestial, Divine, Epic, Legendary, Mythic, Eternal. The pastel palette is the builder's call: one light colour per grade, distinct enough to tell neighbours apart. The mockup's palette is a fine starting point.
- **Empty state.** With no characters yet, a short line points to `/import` and to the ArcheBag `Bag` button.
- **Accessibility.**
  - Tiles are focusable and the tooltip opens on focus too.
  - Each tile has an accessible label (name, count, grade), so colour is never the only cue.
  - The dots have a text equivalent in the tooltip.

### Infra

- An icon cache volume in dev, e2e and prod compose, plus a setting for its path. The backend image runs as `USER app`, so the Dockerfile creates and `chown`s the cache directory; otherwise the named volume mounts root-owned.
- No Caddy change: everything stays under `/api`.

## Tests

**Backend (real Postgres):**
- Parser: both headers (with and without `icon`), quoted character names, empty slots, BOM/CRLF.
  - A gap or a duplicate slot, a mixed `captured_at` or more than 300 slots makes the whole snapshot an error.
  - The `icon` path is normalised.
- Import:
  - first upload of the two-character fixture;
  - the same file again is a full skip;
  - a third, newer snapshot evicts the oldest;
  - an older snapshot than the stored two is skipped;
  - the invariant holds;
  - two users with the same character name stay separate.
- Permissions:
  - no session gives 401;
  - a non-superuser uploading `market.csv` gets `admin only` for that file and their inventory file still imports.
- Read API:
  - own characters only, and another user's character gives 404;
  - change flags `new` / `up` / `down` / null, and a moved stack is null.
- Icons:
  - an invalid name gives 404 without any outbound call;
  - an uppercase name is lowercased first;
  - a miss fetches once and then serves from cache;
  - a fetched Codex placeholder (matching hash) gives 404 and is remembered.
  - **The Codex HTTP call is faked in tests.**

**Frontend:**
- vitest for the grid layout (slot → row and column) and the change-dot mapping.
- vitest for the tooltip text and the placeholder colour per grade.

**e2e:** upload an anonymised `inventory.csv`, open `/inventory`, switch tabs, and hover a tile to see its tooltip.

## Left to the builder

- Where the shared import router lives (`core` or a tiny `imports` module) and how it hands off to services.
- The tooltip component (DaisyUI `tooltip` or a small custom one) and the exact tile size. About 34–40 px fits 10 columns on a phone with the 16 px gutter.
- The icon cache file layout and how a Codex 404 is remembered (a marker file is fine).
- Updating `docs/ai/architecture.md`, `constitution.md` (per-user data rule, no real names in fixtures), `CLAUDE.md` and the roadmap.
