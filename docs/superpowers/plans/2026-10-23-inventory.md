# Inventory (Bag) View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upload ArcheBag `inventory.csv` on `/import`. The newest and previous bag snapshot is stored per user and character. `/inventory` shows a 10-column tile grid, with tooltips and change dots.

**Architecture:**
- A new `imports` module owns `POST /api/import`. It detects each file's kind from its header and dispatches it to `market` (superuser only) or `inventory` (any active user).
- A new `inventory` module holds the parser, the snapshot storage with keep-two eviction, the read API, and a Codex icon cache.
- The frontend gets `lib/inventory/` and a `/inventory` route.

**Tech Stack:** FastAPI, SQLModel + Alembic, PostgreSQL 16, httpx (already installed via httpx-oauth), SvelteKit 2 (Svelte 5 runes), DaisyUI, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-23-inventory-design.md`

## Global Constraints

- Branch `feature/inventory`. It is stacked on `feature/google-login` until PR #17 merges; rebase onto `main` afterwards. Never push, merge or touch `main` without the user's request.
- Commits are `type(scope): description` and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never modify `.env*` except `infra/.env.example`.
- **No real character names in the repo.** Fixtures use `Alpha`, `Bravo` and made-up names.
- **No game icons committed.** The icon cache dir is git-ignored and lives in a compose volume.
- Every inventory read and write is scoped to the signed-in user, by `user.id`.
- Header without icon: `snapshot_id,captured_at,character,slot,item,item_type,item_grade,count`. Header with icon: the same plus `,icon`.
- Grid: 10 columns, slot 1 is top-left, row `floor((s-1)/10)+1`, column `(s-1)%10+1`. Max 300 slots.
- Grades 0..12: None, Basic, Grand, Rare, Arcane, Heroic, Unique, Celestial, Divine, Epic, Legendary, Mythic, Eternal.
- Codex URL: `https://archeagecodex.com/items/{name}.png`.
  - Unknown names return `200` with a 1891-byte placeholder whose SHA-256 is `17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a` (fetched 2026-10-23).
  - `icon_item_0352` (Leather) is a real 3625-byte icon.
- Icon names: lowercase, `^[a-z0-9_]{1,64}$`.
- Module rule: each module has the same core files, and any other file starts with a one-line reason comment. Modules use each other's services and csv constants, never each other's models.
- Naive UTC datetimes in the DB. The frontend appends `'Z'` before `new Date()`, like `ListingsTable.svelte:17`.
- Backend tests use a real Postgres:
  ```
  docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16-alpine
  cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest
  ```
  Tests never call Codex.

## Review Focus

1. **Character names with a comma, quotes or non-ASCII letters** (`"Zażółć, \"Gęś\""`). They must import, list and open via the URL-encoded path. Pinned in Task 4: `test_character_name_with_comma_and_unicode`.
2. **Two clicks in the same second.** The addon reuses `snapshot_id`, so one `(character, snapshot_id)` holds two full runs `1..N,1..N`. Keep the **last complete run** instead of rejecting both. Pinned in Task 2: `test_same_second_double_click_keeps_last_run`.
3. **The same snapshot in two files of one drop.** The first file inserts it, the second skips it, and the invariant holds for both. Pinned in Task 3: `test_same_snapshot_in_two_files_of_one_upload`.
4. **Re-uploading an old file after newer snapshots are stored.** Nothing is deleted and everything is skipped. Pinned in Task 3: `test_older_file_after_newer_is_noop`.
5. **A completely empty bag snapshot.** It is valid: all tiles dark, no change flags, and nothing listed for the items that left. Pinned in Task 4: `test_empty_bag_snapshot`.

---

### Task 1: Shared `POST /api/import` with per-file permissions

**Files:**
- Create: `backend/app/imports/__init__.py`, `backend/app/imports/schemas.py`, `backend/app/imports/services.py`, `backend/app/imports/router.py`.
- Modify:
  - `backend/app/market/schemas.py`: drop `ImportRowError` and `ImportFileResult`, import them from `app.imports.schemas`.
  - `backend/app/market/services.py`: import path.
  - `backend/app/market/router.py`: delete the `/import` route.
  - `backend/app/main.py`: mount the imports router.
  - `backend/seed.py`: import path.
  - `backend/app/auth/dependencies.py`: add `current_active_user = fastapi_users.current_user(active=True)`.
- Modify (frontend):
  - `frontend/src/lib/market/api.ts`: `uploadFiles` posts to `/import`.
  - `frontend/src/routes/import/+page.svelte`: any signed-in user. Copy: "Drop `market.csv`, `listings.csv` (admin only) and `inventory.csv`."
  - `frontend/src/routes/+layout.svelte`: Import and Inventory links for `user.isLoggedIn`.
  - `frontend/src/lib/core/api.d.ts`: regenerate.
- Test:
  - `backend/tests/imports/__init__.py`, `backend/tests/imports/test_router.py` (new);
  - `backend/tests/market/test_import.py`: `upload()` and the permission test move to `/api/import`;
  - `frontend/src/lib/market/ImportDropzone.test.ts`, `frontend/src/test/routes/import.page.test.ts`: mock route `'/import'`.

**Interfaces:**
- Produces:
  - `app.imports.schemas.ImportFileResult` and `ImportRowError`, with the same fields; `kind: Literal["listings", "market", "inventory"] | None`.
  - `app.imports.services.import_file(session, user: User, filename: str, data: bytes) -> ImportFileResult`.
  - `app.imports.schemas.failed(filename, kind, rows, reason) -> ImportFileResult`, moved from `market.services._failed` and now public. It lives in `schemas.py`, not `services.py`, because `market.services` imports it while `imports.services` imports `market.services`; a function there would make the imports circular.
  - `POST /api/import` (multipart `files`) → `list[ImportFileResult]`. It requires `current_active_user` and is limited to `10/minute`.
- Task 3 adds the `inventory` branch to `import_file`.

- [ ] **Step 1: Write the failing tests** (`tests/imports/test_router.py`)

  ```python
  async def test_import_requires_signed_in_user(client):  # 401 without cookie
      r = await client.post("/api/import", files=[("files", ("m.csv", b"x", "text/csv"))])
      assert r.status_code == 401

  async def test_market_file_admin_only_per_file(client, make_user, login):
      user, pwd = await make_user(superuser=False); await login(client, user.email, pwd)
      r = await client.post("/api/import", files=[("files", ("market.csv", MARKET_FIXTURE_BYTES, "text/csv"))])
      assert r.status_code == 200
      [res] = r.json()
      assert res["kind"] == "market" and res["inserted"] == 0
      assert res["errors"] == [{"line": 0, "reason": "admin only"}]
      assert res["inserted"] + res["updated"] + res["skipped"] + res["error_count"] == res["rows"]

  async def test_superuser_market_import_still_works(superuser_client):
      # Same counts as the old /api/market/import sample test
      ...

  async def test_unknown_header(superuser_client):
      # kind None, error "unknown header"
      ...

  async def test_old_market_import_route_is_gone(superuser_client):
      # POST /api/market/import → 404 or 405
      ...
  ```

  Also point `tests/market/test_import.py::upload` and `test_import_requires_superuser` at `/api/import`. The latter becomes `test_import_requires_signed_in_user` and keeps only the 401 assert.

  `MARKET_FIXTURE_BYTES` is the real `backend/tests/market/fixtures/market.csv`, rewritten with `rewrite_fixture` for unique item types.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/imports tests/market/test_import.py -q`.

  Expected: 404s and an ImportError on `app.imports`.

- [ ] **Step 3: Implement the backend**

  `import_file` works like this:
  1. The size check (> `MAX_FILE_BYTES`) returns `failed(..., None, 0, "file larger than 50 MB")`.
  2. Read the header: decode the first line with `utf-8-sig` and strip `\r\n`.
  3. If the header is `LISTINGS_HEADER` or `MARKET_HEADER` and the user is not a superuser, `rows` is the number of non-empty lines after the header, and the result is `failed(filename, kind, rows, "admin only")`.
  4. Otherwise call `market.services.import_csv`.
  5. An unknown header is handed to `market.services.import_csv`, which already answers `unknown header`.

  `MAX_FILE_BYTES` stays in `market.services`; import it from there.

- [ ] **Step 4: Implement the frontend**

  - Change the upload URL.
  - Gate `/import` on `user.isLoggedIn` instead of `is_superuser`.
  - Add the nav links. `/inventory` gives 404 until Task 6, which is acceptable inside the branch.
  - Regenerate `api.d.ts`. Follow the CLAUDE.md commands, with `GOOGLE_CLIENT_ID=x GOOGLE_CLIENT_SECRET=y`.

- [ ] **Step 5: Run the tests and watch them pass**

  Run the full backend suite, `ruff check . && ruff format --check .`, and `cd frontend && npm test && npm run check`.

  Expected: all pass.

- [ ] **Step 6: Commit**

  `feat(imports): one /api/import for all CSVs; market files admin only`

---

### Task 2: Inventory models, migration and CSV parser

**Files:**
- Create:
  - `backend/app/inventory/__init__.py`, `backend/app/inventory/models.py`;
  - `backend/app/inventory/csv_format.py`, with the first line `# Parses ArcheBag inventory.csv into validated per-character snapshots.`;
  - `backend/alembic/versions/0002_inventory.py`, generated with `alembic revision --autogenerate -m "inventory"`.
- Modify: `backend/tests/conftest.py`, adding `from app.inventory.models import InventorySnapshot, InventorySlot  # noqa: F401` so `create_all` sees them.
- Test:
  - `backend/tests/inventory/__init__.py`, `backend/tests/inventory/test_csv_format.py`;
  - `backend/tests/inventory/fixtures/inventory.csv`. It is anonymised from ArcheMarket `llm-wiki/sources/raw/ingame/2026-10-23-step7c/inventory.csv`: replace the two real character names with `Alpha` and `Bravo` (a `sed` over the `character` column). Verify with `grep` that neither real name remains. It has 241 lines: Alpha 90 slots, 56 filled; Bravo 150 slots, 112 filled.

**Interfaces:**
- Produces, in `app.inventory.models`:
  - `InventorySnapshot(id: int PK, user_id: uuid FK user.id ondelete CASCADE, character: str(64), snapshot_id: int bigint, captured_at: datetime, slot_count: int)`, with UNIQUE `(user_id, character, snapshot_id)` named `uq_inventory_snapshot`.
  - `InventorySlot(snapshot: int FK inventory_snapshot.id ondelete CASCADE PK, slot: int PK, item: str(120)|None, item_type: int|None, item_grade: int|None, count: int, icon: str(64)|None)`.
- Produces, in `app.inventory.csv_format`:
  - `INVENTORY_HEADER` and `INVENTORY_HEADER_ICON`;
  - `@dataclass SlotRow(slot, item, item_type, item_grade, count, icon)`;
  - `@dataclass Snapshot(character, snapshot_id, captured_at: datetime, slots: list[SlotRow], lines: int)`;
  - `@dataclass ParsedInventory(rows: int, snapshots: list[Snapshot], errors: list[RowError], skipped: int = 0)`. `skipped` counts the lines of the earlier runs that the double-click rule drops;
  - `parse_inventory(data: bytes) -> ParsedInventory`, which raises `CsvFormatError`;
  - `normalize_icon(raw: str) -> str | None`.
- Reuses `RowError` and `CsvFormatError` from `app.market.csv_format`.

- [ ] **Step 1: Write the failing tests** (`tests/inventory/test_csv_format.py`)

  - `test_fixture_two_characters`:
    - `rows == 240`;
    - two snapshots, `Alpha` with 90 slots and `Bravo` with 150;
    - filled counts 56 and 112;
    - `errors == []`.
  - `test_header_with_icon`: an extra `,icon` column with `Game/ui/icon/icon_item_0352.dds` gives `icon == "icon_item_0352"`, and an empty value gives `None`.
  - `test_normalize_icon`:
    - `"Game/ui/icon/ICON_Item_0352.dds"` gives `"icon_item_0352"`;
    - `""` gives `None`;
    - `"../etc/passwd"` gives `None`, because it fails the regex after normalising.
  - `test_empty_slot_line`: `1,1,Alpha,2,,,,0` gives `SlotRow(2, None, None, None, 0, None)`.
  - `test_quoted_character_name`: `"Zażółć, ""Gęś"""` gives `character == 'Zażółć, "Gęś"'`.
  - These each make every line of the snapshot an error with one reason, and no snapshot is returned:
    - `test_gap_in_slots_rejects_snapshot`: slots 1,2,4;
    - `test_duplicate_slot_rejects_snapshot`;
    - `test_mixed_captured_at_rejects_snapshot`;
    - `test_more_than_300_slots_rejects_snapshot`.
  - `test_same_second_double_click_keeps_last_run`:
    - slots `1,2,3,1,2,3` for one `(character, snapshot_id)` give a single 3-slot snapshot with the second run's items;
    - the first run's 3 lines are counted as `skipped`, carried as `ParsedInventory.skipped: int`. Add that field.
    - This is Review Focus 2.
  - `test_bad_row`: a non-integer `count` gives that line as a `RowError`, and its snapshot is rejected.
  - `test_bom_crlf_and_unknown_header`.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/inventory/test_csv_format.py -q`.

  Expected: an ImportError.

- [ ] **Step 3: Implement the models and the parser**

  The parser groups lines by `(character, snapshot_id)` in file order. Inside a group, each `slot == 1` starts a new run, and the last run is kept. That run is valid when its slots are exactly `1..N`, `N ≤ 300`, and every line has the same `captured_at`.

  Converting epoch seconds to naive UTC is the same as the market's `_ts`. Reuse it by importing `app.market.csv_format._ts`, or copy it into the parser with a comment.

- [ ] **Step 4: Write the migration**

  Run `uv run alembic revision --autogenerate -m "inventory"` against a fresh DB at head, then `alembic upgrade head && alembic check`.

  Expected: no new operations.

- [ ] **Step 5: Run the tests and watch them pass**

  Run the full suite and ruff.

  Expected: all pass.

- [ ] **Step 6: Commit**

  `feat(inventory): snapshot models, migration and inventory.csv parser`

---

### Task 3: Inventory import (keep two newest per character)

**Files:**
- Create: `backend/app/inventory/services.py`, `backend/app/inventory/schemas.py`.
- Modify: `backend/app/imports/services.py`, with the inventory header branch.
- Test: `backend/tests/inventory/test_import.py`.

**Interfaces:**
- Consumes: `parse_inventory` (Task 2); `ImportFileResult` and `failed`, both from `app.imports.schemas` (Task 1).
- Produces: `app.inventory.services.import_csv(session, user_id: uuid.UUID, filename: str, data: bytes) -> ImportFileResult`, with `kind="inventory"`.

- [ ] **Step 1: Write the failing tests** (via `POST /api/import`, using a `superuser_client` or a `make_user` client)

  - `test_first_upload`: the fixture gives `rows=240`, `inserted=240`, `skipped=0`, `error_count=0`. Two snapshots are stored for this user.
  - `test_reupload_is_noop`: the same file again gives `inserted=0, skipped=240`.
  - `test_third_snapshot_evicts_oldest`:
    - upload snapshots t1, t2 and t3 for `Alpha`, as three files built from the fixture with different `snapshot_id` and `captured_at`;
    - stored are t2 and t3;
    - t1's slots are gone, via the cascade.
  - `test_older_file_after_newer_is_noop`: t2 and t3 are stored, then t1 is uploaded. The result is `inserted=0, skipped=90`, and t2 and t3 are untouched. This is Review Focus 4.
  - `test_same_snapshot_in_two_files_of_one_upload`: one request with two files that hold the same snapshot. The first file inserts it, the second skips it, and the invariant holds for both. This is Review Focus 3.
  - `test_users_are_separate`: two users upload the same fixture, and each stores their own `Alpha` and `Bravo`.
  - `test_invariant_with_errors`: a file with one rejected snapshot and one valid one satisfies `inserted + skipped + error_count == rows`.
  - `test_non_superuser_can_import_inventory`: a `make_user(superuser=False)` client gets `inserted > 0`.

- [ ] **Step 2: Run the tests and watch them fail**

  Expected: the result is `unknown header`.

- [ ] **Step 3: Implement**

  Per character in the parsed file, in one transaction per file:
  1. Load the stored snapshots for `(user_id, character)`.
  2. Candidates are the stored ones plus the parsed ones not yet stored, keyed by `snapshot_id`. Keep the top 2 by `(captured_at, snapshot_id)`.
  3. Insert the parsed ones that made the top 2 and delete the stored ones that did not.
  4. Accounting: `inserted` is the lines of inserted snapshots. `skipped` is the lines of parsed snapshots that were already stored or did not make the top 2, plus `parsed.skipped`.

  Slots are inserted in chunks, like the market import. Use the same `CHUNK_ROWS` idea: 7 columns, so 2000 rows stays under the limit.

  If `SQLAlchemyError` is raised, roll back and return `failed(... "database error: X")`, like the market import.

- [ ] **Step 4: Run the tests and watch them pass**

  Run the full suite.

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(inventory): import keeps the two newest snapshots per character`

---

### Task 4: Inventory read API

**Files:**
- Create: `backend/app/inventory/router.py`, mounted in `app/main.py` under `/api`, prefix `/inventory`.
- Modify: `backend/app/inventory/schemas.py`, `backend/app/inventory/services.py`.
- Test: `backend/tests/inventory/test_queries.py`.

**Interfaces:**
- Produces:
  - `GET /api/inventory/characters` → `list[CharacterRead]`, where `CharacterRead(character: str, captured_at: datetime, previous_captured_at: datetime | None, slot_count: int, filled: int)`, sorted by name.
  - `GET /api/inventory/characters/{character}` → `BagRead(character, captured_at, previous_captured_at, slots: list[SlotRead])`, where `SlotRead(slot, item, item_type, item_grade, count, icon, change: Literal["new", "up", "down"] | None, delta: int | None)`. Unknown names give 404.
  - Both require `current_active_user`.

- [ ] **Step 1: Write the failing tests**

  - `test_characters_only_own`: user A sees `Alpha` and `Bravo`, user B sees `[]`, and user B's GET of `/characters/Alpha` gives 404.
  - `test_bag_slots_in_order_with_empty_slots`: 90 slots, `slots[0].slot == 1`, and empty slots have `item is None, count == 0, change is None`.
  - Change flags, where the previous snapshot has `Leather×100` in slot 4 and `Iron Ore×5` in slot 7:

    | Newest snapshot | Expected |
    |---|---|
    | `Leather×100` in slot 12, `Iron Ore×5` in slot 7 | `test_moved_stack_is_no_change`: slot 12 has `change None, delta 0` |
    | `Leather×150` | `test_up`: `change "up", delta 50` |
    | `Leather×40` | `test_down`: `"down"`, `-60` |
    | a new `Copper Ingot×3` | `test_new`: `change "new"`, `delta 3` |

    - `test_split_stack_sums_per_item`: Leather in two slots, 60 + 60, against 100 before gives `"up"` and `+20` on **both** slots.
    - `test_no_previous_snapshot`: every `change` is None and `delta` is None.
  - `test_empty_bag_snapshot`: the newest snapshot is all empty and the previous one had items. Every slot is empty and every `change` is None. This is Review Focus 5.
  - `test_character_name_with_comma_and_unicode`: import a character named `Zażółć, "Gęś"`. It is listed, and its bag opens through `quote(name, safe="")`. This is Review Focus 1.
  - `test_requires_login`: both endpoints give 401 without a cookie.

- [ ] **Step 2: Run the tests and watch them fail**

  Expected: 404 on the routes.

- [ ] **Step 3: Implement**

  - `change` and `delta` are computed in Python. Sum `count` by `(item_type, item_grade)` for the newest and the previous snapshot, then set `delta = now - before` on each filled slot.
  - `change` is `"new"` when the key is absent before, `"up"` or `"down"` from the sign of the delta, and None when the delta is 0.
  - With no previous snapshot, both fields are None.

- [ ] **Step 4: Run the tests and watch them pass**

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(inventory): per-user characters and bag read API with change flags`

---

### Task 5: Codex icon cache

**Files:**
- Create: `backend/app/inventory/icons.py`, with the first line `# Fetches item icons from ArcheAge Codex once and serves them from a local cache.`
- Modify:
  - `backend/app/inventory/router.py`: add `GET /api/inventory/icons/{name}.png`, public.
  - `backend/app/core/settings.py`: `icon_cache_dir: str = "/app/icon-cache"`.
  - `backend/Dockerfile`: `mkdir -p /app/icon-cache` inside the existing `chown` RUN.
  - `infra/compose/docker-compose.{dev,e2e,prod}.yml`: a named volume `icon_cache` at `/app/icon-cache` on the backend.
  - `.gitignore`: `icon-cache/` and `.superpowers/`.
  - `backend/tests/conftest.py`: `os.environ["ICON_CACHE_DIR"]` pointing to a session tmp dir.
- Test: `backend/tests/inventory/test_icons.py`.

**Interfaces:**
- Produces:
  - `CODEX_PLACEHOLDER_SHA256 = "17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a"`;
  - `MAX_FETCHES_PER_MINUTE = 60`;
  - `async def fetch_codex(name: str) -> bytes | None`, the one network call, faked in tests;
  - `async def get_icon(name: str) -> bytes | None`, where None means missing;
  - the route returns `Response(content, media_type="image/png", headers={"Cache-Control": "public, max-age=604800"})`, 404 when missing or invalid, and 503 when the fetch budget is used up.

- [ ] **Step 1: Write the failing tests** (monkeypatch `icons.fetch_codex` with a counting fake)

  - `test_invalid_name_404_without_fetch`: `ICON..x`, `a/b` and a 65-character name each give 404, and the fake is called 0 times.
  - `test_uppercase_is_lowercased`: `/icons/ICON_ITEM_0352.png` fetches `icon_item_0352`.
  - `test_miss_fetches_once_then_cache`: two GETs give 200 with the same bytes, and the fake is called once.
  - `test_placeholder_is_missing_and_remembered`: the fake returns bytes whose SHA-256 equals the constant, for example by monkeypatching the constant to `sha256(b"ph")` and returning `b"ph"`. Two GETs give 404, and the fake is called once.
  - `test_fetch_error_is_not_cached`: the fake returns None, which stands for a network error or a non-200. The GET is 404, and the next GET calls the fake again.
  - `test_fetch_budget`: with `MAX_FETCHES_PER_MINUTE` monkeypatched to 1, the second different miss gives 503 and is not called; the first name, now cached, still gives 200.
  - `test_icons_are_public`: no cookie gives 200 for a cached icon.

- [ ] **Step 2: Run the tests and watch them fail**

  Expected: 404 or ImportError.

- [ ] **Step 3: Implement**

  - **Cache files:** `{dir}/{name}.png` for an icon and `{dir}/{name}.missing` for a remembered placeholder.
  - **`fetch_codex`:** uses `httpx.AsyncClient(timeout=5)`. Anything other than a 200 `image/png` returns None, and so does an `httpx.HTTPError`.
  - **Fetch budget:** a module-level deque of fetch timestamps. When it is full, answer 503 without calling Codex.
    - The budget is per process: `shortcut: per-process window (2 prod workers → up to 2×), move to the shared limiter if Codex complains`.
  - **Concurrent misses:** two simultaneous misses for the same name may both fetch, and that is accepted: `shortcut: no per-name lock, the second write is identical`.
  - **Writes:** write to a temp file, then `os.replace`.

- [ ] **Step 4: Run the tests and watch them pass**

  Run the full suite, `bash infra/tests/*.sh`, and `docker compose -f infra/compose/docker-compose.dev.yml config -q` for each compose file.

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(inventory): Codex icon cache with placeholder detection and fetch budget`

---

### Task 6: `/inventory` page

**Files:**
- Create:
  - `frontend/src/lib/inventory/api.ts`, with `fetchCharacters()`, `fetchBag(character)` and `iconUrl(name)`.
  - `frontend/src/lib/inventory/grades.ts`, with `GRADE_NAMES: string[13]`, `GRADE_COLORS: string[13]` (pastel, from the mockup palette), `gradeName(g)` and `gradeColor(g)`; out-of-range and null use index 0.
  - `frontend/src/lib/inventory/grid.ts`, with `slotPosition(slot): {row, col}`, `tileLabel(s: SlotRead): string` and `changeDot(change): 'up'|'down'|'new'|null`.
  - `frontend/src/lib/inventory/InventoryGrid.svelte`, `frontend/src/lib/inventory/InventoryTile.svelte`.
  - `frontend/src/routes/inventory/+page.svelte`.
- Modify:
  - `frontend/svelte.config.js`: `img-src` adds `apiOrigin`.
  - `frontend/src/lib/core/types.ts`: re-export `CharacterRead`, `BagRead` and `SlotRead`.
  - `frontend/src/lib/core/api.d.ts`: regenerate.
- Test:
  - `frontend/src/lib/inventory/grid.test.ts`, `frontend/src/lib/inventory/grades.test.ts`;
  - `frontend/src/test/routes/inventory.page.test.ts`.

**Interfaces:**
- Consumes the Task 4 and Task 5 endpoints.
- `tileLabel` builds the tooltip text and the `aria-label`. The exact copy is: `"{item} · {gradeName} ({grade}) · ×{count}"`, plus `" · +{delta}"` or `" · {delta}"` when `delta` is non-zero, plus `" · new"` when `change == 'new'`. An empty slot is `"Empty slot {slot}"`.

- [ ] **Step 1: Write the failing tests**

  - `slotPosition(1)` is `{row:1,col:1}`, `slotPosition(10)` is `{row:1,col:10}`, `slotPosition(11)` is `{row:2,col:1}`, and `slotPosition(150)` is `{row:15,col:10}`.
  - `tileLabel`:
    - `Leather` grade 0, count 412, delta 120 gives `"Leather · None (0) · ×412 · +120"`;
    - a new item gives `"Copper Ingot · Basic (1) · ×3 · +3 · new"`;
    - an empty slot gives `"Empty slot 7"`.
  - `gradeName(6) === 'Unique'`, `gradeColor(99) === GRADE_COLORS[0]`, and all 13 colours are distinct.
  - `inventory.page.test.ts`, with mocked fetch:
    - tabs render as `Alpha · 90` and `Bravo · 150`;
    - clicking Bravo sets `?character=Bravo`;
    - 150 tiles render;
    - a tile with `icon` renders `<img src=".../inventory/icons/icon_item_0352.png">`, and after an `error` event it falls back to a coloured `div`;
    - the empty state shows a link to `/import` when there are no characters.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `cd frontend && npx vitest run src/lib/inventory src/test/routes/inventory.page.test.ts`.

  Expected: FAIL.

- [ ] **Step 3: Implement**

  **Tile:**
  - A 36 px square: `tabindex=0`, `aria-label={tileLabel}`, and a DaisyUI `tooltip` whose `data-tip` is the same text.
  - The background is `gradeColor` when there is no icon, or when the icon failed (`onerror` sets a local `$state`).
  - The count sits bottom-right when it is above 1.
  - The change dot sits top-left: green-500 for up, red-500 for down, blue-500 for new.
  - An empty slot is `bg-base-300`.

  **Grid:** CSS grid, `grid-template-columns: repeat(10, 36px)`, gap 3 px, in slot order. Below 420 px the tile size may shrink to fit.

  **Page:**
  - Tabs: DaisyUI `tabs tabs-boxed`.
  - The selected character comes from `?character=` and defaults to the first. A `seq` guard ignores stale responses, as on `/market`.
  - Times show as `new Date(x + 'Z').toLocaleString('en-GB')`, with "previous: —" when there is none.
  - Page title: `Inventory · AA Tracker`.

- [ ] **Step 4: Run the tests and watch them pass**

  Run `npm test && npm run check`, then `env -u PUBLIC_PASSWORD_LOGIN npm run build`.

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(frontend): /inventory page with character tabs, tile grid and tooltips`

---

### Task 7: e2e, docs, roadmap

**Files:**
- Create:
  - `frontend/e2e/fixtures/inventory.csv`: a small anonymised file, 2 characters × 20 slots, a few items, made-up names `Alpha` and `Bravo`.
  - `frontend/e2e/inventory.spec.ts`.
- Modify:
  - `docs/architecture.md`: the imports and inventory modules, tables, endpoints and icon cache.
  - `docs/constitution.md`:
    - "Inventory data is per user; every query filters by the signed-in user."
    - "No real character names in fixtures."
    - "Game icons are never committed."
  - `CLAUDE.md`: modules list, `/inventory` and `/import` routes, the `icon_cache` volume.
  - `docs/roadmap.md`: Done row, plus the Planned rows "Warehouse and house chests", "ArcheBag `icon` column" and "Player registration".
  - `docs/progress.md`.
  - `README.md`: the Importing section mentions `inventory.csv` from `Documents/Addon/archebag/`.

- [ ] **Step 1: Write the e2e spec**

  Using the stored login state:
  1. Upload `inventory.csv` on `/import`. The result row shows kind `inventory`.
  2. Open `/inventory`. Tab `Alpha · 20` is selected.
  3. Click `Bravo · 20`; the URL has `character=Bravo`.
  4. Focus a filled tile; its `aria-label` contains `×`.

- [ ] **Step 2: Run the e2e suite**

  Run the docker equivalents of `make e2e-up e2e-migrate e2e-seed e2e-test`, as in previous plans, with `-p e2e-inv`.

  Expected: the previous 10 tests plus the new ones all pass. Then tear down.

- [ ] **Step 3: Update the docs**

  As listed above.

- [ ] **Step 4: Commit**

  `test(e2e): inventory journey; docs: inventory module and rules`
