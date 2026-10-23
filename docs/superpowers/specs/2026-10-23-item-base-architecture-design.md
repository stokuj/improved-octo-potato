# Item base and project architecture: design

Status: approved, 2026-10-23. It merges two independent architecture proposals; the owner chose between them where they differed. Decisions and their reasons are in ADR-0007 to ADR-0012 (`docs/adr/`); this document is the concrete shape a builder plans from. ADRs may be corrected as the build moves.

Related:
- the `/market` page spec: `2026-10-23-market-auction-house-design.md`;
- the addon contract: ArcheMarket `llm-wiki/project/step7e-design.md` (new headers).

## Intent

- **(a) Market:** prices for every item.
- **(c) Crafting, later:** what it costs to make an item versus what it sells for. Crafting needs the account's totals over every character and chest.

To get there the app needs an **item base** that all data points at, uniform import and logging patterns, and provenance on market rows. Valuing the player's items is not a goal.

## Non-goals

- player registration;
- several game accounts per user;
- recipes and crafting;
- a reject flow for items;
- blocking forgers and per-user market rows (the schema must not block them);
- a data migration: the schema gets a fresh baseline and the CSVs are re-imported.

## Modules

```
backend/app/
  core/       settings, db, errors, rate_limit, time (utcnow, GAME_TZ moved here), logging (NEW)
  auth/       unchanged
  items/      NEW: Item model, resolve/lookup services, ItemAdmin (editable)
  market/     MarketDay, Listing (+user_id); write primitives; option-A reads; router; admin
  inventory/  snapshots, slots (item_id), chest names; write primitives; grids, all-items read; router; icons.py (Codex, unchanged)
  imports/    ImportRun, ImportIssue; the pipeline; POST /api/import; admin views
              connector.py (protocol, registry, shared row helpers)
              archemarket.py (market + listings connectors), archebag.py (inventory + chests connectors)
  admin/      sqladmin setup, registers every module's views
```

- Dependencies run one way: `imports -> items, market, inventory`; `market -> items`; `inventory -> items`; everything `-> core`.
- `market` and `inventory` never see a header or a column (ADR-0009). Their reads may join the `item` table in raw SQL (ADR-0012).
- `items/admin.py` calls `imports.services.record_admin_edit(...)`. This does not create an import cycle, because only `admin/setup` imports the admin files.

**Kept unchanged:**
- auth and admin auth;
- the single limiter;
- `AppError`/`NotFoundError`;
- the Codex client;
- the keep-two snapshot rule and the same-second double-click runs;
- chest names, where empty means "no change";
- `ON CONFLICT … WHERE stored.captured_at < new` with `RETURNING (xmax = 0)`;
- 2 000-row chunks;
- the 50 MB limit;
- the `ImportFileResult` shape (plus `run_id`);
- the `/items` grids and `chestOwner`.

## Tables

All datetimes are naive UTC, money is `bigint` copper, and `grade` is the raw game int. One new `0001_baseline` replaces migrations `0001`–`0004`.

```sql
item (                                  -- CHANGED, moves to items/
  id serial PK,
  item_type int NOT NULL, grade smallint NOT NULL,       -- grade was item_grade; both were nullable
  name varchar(120) NOT NULL,                            -- no longer unique
  category varchar(64) NULL,                             -- NULL shows as "Other"
  npc_price bigint NULL,
  verified bool NOT NULL,
  created_by uuid NULL REFERENCES "user" ON DELETE SET NULL,
  first_seen_at timestamp NOT NULL,                      -- captured_at of the first row naming it
  changed_at timestamp NOT NULL,                         -- source time of the newest applied value; admin edit = utcnow()
  UNIQUE (item_type, grade)                              -- uq_item_type_grade
)  -- index on name (old-header listings lookup)

market_day (                            -- CHANGED: + user_id
  item_id int REFERENCES item, day date, daily_avg, weekly_avg, min, max, volume bigint,
  scan_id bigint, captured_at timestamp,
  user_id uuid NOT NULL REFERENCES "user" ON DELETE RESTRICT,
  PRIMARY KEY (item_id, day)
)

listing (                               -- CHANGED: + user_id, in the key
  item_id int REFERENCES item, user_id uuid NOT NULL REFERENCES "user" ON DELETE RESTRICT,
  scan_id bigint, rank smallint, captured_at timestamp, status varchar(20),
  unit_price bigint NULL, listing_price bigint NULL, stack int NULL,
  PRIMARY KEY (item_id, user_id, scan_id, rank)
)  -- index (item_id, captured_at DESC)

inventory_snapshot (                    -- CHANGED: chest place key, + saved_by
  id serial PK, user_id uuid REFERENCES "user" ON DELETE CASCADE,
  container varchar(5),                 -- bag | bank | chest
  chest smallint,                       -- 1..10 for a chest, else 0
  character varchar(64),                -- bag/bank: the owner; chest: ''
  saved_by varchar(64),                 -- the character that saved it (every kind)
  snapshot_id bigint, captured_at timestamp, slot_count smallint,
  UNIQUE (user_id, container, chest, character, snapshot_id)
)  -- index (user_id, container, chest, character, captured_at DESC, snapshot_id DESC)

inventory_slot (                        -- CHANGED: item_id replaces item, item_type, item_grade
  snapshot int REFERENCES inventory_snapshot ON DELETE CASCADE, slot smallint,
  item_id int NULL REFERENCES item ON DELETE RESTRICT,   -- NULL = empty slot
  count int,
  PRIMARY KEY (snapshot, slot)
)  -- index (item_id)

inventory_chest_name                    -- unchanged

import_run (                            -- NEW
  id bigserial PK, user_id uuid NULL REFERENCES "user" ON DELETE SET NULL,
  request_id varchar(64) NOT NULL,
  connector varchar(20) NULL,           -- market | listings | inventory | chests | admin_edit; NULL = unknown header
  filename varchar(255) NOT NULL, status varchar(10) NOT NULL,   -- ok | failed
  rows, inserted, updated, skipped, error_count int NOT NULL,    -- the sum rule holds on every row
  started_at, finished_at timestamp NOT NULL
)  -- index (user_id, started_at DESC)

import_issue (                          -- NEW
  id bigserial PK, run_id bigint NOT NULL REFERENCES import_run ON DELETE CASCADE,
  kind varchar(20) NOT NULL,            -- row_error | file_error | item_new | item_changed | item_verified | item_mismatch
  line int NOT NULL DEFAULT 0,          -- 0 = not tied to one line
  item_id int NULL REFERENCES item ON DELETE SET NULL,
  field varchar(20) NULL, old_value text NULL, new_value text NULL, reason text NULL
)  -- indexes (run_id), (item_id)
```

- Later, `recipe(item_id → item)` and `recipe_ingredient(item_id → item)`, as in `backend/frozen/crafting/models.py`.
- Later, `user.is_blocked` and `market_day` PK `(item_id, day, user_id)` (ADR-0011).

## Mechanisms

### Connector pipeline (`imports/`)

```python
class Connector[P](Protocol):
    kind: str                         # ImportFileResult.kind and import_run.connector
    headers: tuple[str, ...]          # exact headers, old and new
    admin_only: bool
    def parse(self, header: str, rows: Iterator[tuple[int, list[str]]]) -> Parsed[P]          # pure
    async def store(self, session, ctx: RunContext, parsed: Parsed[P], ids: dict[ItemKey, int]) -> Counts

ItemKey = tuple[int, int]             # (item_type, grade)
@dataclass class ItemFacts: name: str; category: str | None; npc_price: int | None; seen_at: datetime
@dataclass class Parsed[P]: rows: int; skipped: int; errors: list[RowError]; items: dict[ItemKey, ItemFacts]; payload: P
```

- `None` in `ItemFacts` means "the file does not say".
- `parse` reduces the facts per key: the newest `seen_at` wins per field, and `None` never replaces a value.

One file goes through `import_file(session, user, filename, data) -> ImportFileResult`:
1. Size check, then read the header and find the connector in `BY_HEADER`. An unknown header, a refused `admin_only` file and a `CsvFormatError` each become a failed run with one `file_error`, in today's `failed()` shape.
2. In the file's transaction:
   1. `items.resolve`;
   2. `connector.store`;
   3. assert the sum rule;
   4. insert the run and its issues;
   5. commit.
3. On a DB error or a failed sum-rule assert: roll back, then write a `failed` run with one `file_error` in a fresh transaction. Every file leaves a run.
4. Log `import.done` or `import.failed` at the technical layer. Return the result with `run_id` and the first 100 errors.

Rules shared by every connector:
- A row dated more than one day in the future is a row error.
- At most 1 000 `row_error` issues are stored per run, then one "…and N more". The counts stay exact.

Headers:
- `market`: `MARKET_HEADER_V1` (today's) and `MARKET_HEADER_V2` (with `,category`).
- `listings`: `LISTINGS_HEADER_V1` (today's) and `LISTINGS_HEADER_V2` (with `,item_type,item_grade`).
- `inventory`, `chests`: today's 7d headers.

Rows without a key:
- **V1 listings** have no type or grade. A row matches an item only when its name is unique in the base; otherwise it is a row error. These rows never create items.
- **Status rows** (`rank` 0) in V2 have empty type and grade. They resolve by unique name too, but an unknown or ambiguous name makes the row **skipped**, not an error, because a status row only says "no offer". *Builder's call.*
- In both cases, one scan page can hold offers of several grades. Each row goes to its own item.

### Item resolve and verification (`items/services.py`)

```python
@dataclass(frozen=True) class Actor: user_id: uuid.UUID; is_admin: bool
async def resolve(session, facts: dict[ItemKey, ItemFacts], actor: Actor) -> tuple[dict[ItemKey, int], list[ItemIssue]]
async def ids_by_unique_name(session, names: set[str]) -> dict[str, int]
```

1. `INSERT … ON CONFLICT (item_type, grade) DO NOTHING RETURNING …`, sorted by key. A new row gets:
   - `verified = actor.is_admin`;
   - `created_by = actor.user_id`;
   - `first_seen_at = changed_at = seen_at`.

   Each returned row is an `item_new` issue.
2. `SELECT … WHERE (item_type, grade) IN (…) ORDER BY item_type, grade FOR UPDATE`.
3. Decide each field in Python (`name`, `category`, `npc_price`). An incoming `None` is never applied.

   | stored | actor | differs, `seen_at > changed_at` | differs, older |
   |---|---|---|---|
   | unverified | admin | apply, `item_changed`; set verified, `item_verified` | verify only |
   | verified | admin | apply, `item_changed` | ignore |
   | unverified | player | apply, `item_changed` | ignore |
   | verified | player | keep, `item_mismatch` (this includes filling an empty field) | keep, `item_mismatch` |

   - An admin file verifies an unverified item even when no field changes.
   - Applied changes set `changed_at` to the newest applied `seen_at`.
4. One executemany `UPDATE` writes the changed rows.

Inserts and locks run in key order, so there are no deadlocks. Uploads that share items wait for each other.

**`ItemAdmin`:**
- may edit `name`, `category`, `npc_price` and `verified`;
- may not create or delete items;
- filters by `verified` and `category`, and searches by name;
- every edit sets `changed_at = utcnow()` and records an `admin_edit` run with one issue per changed field.

### Market import

- `store_days(session, user_id, rows, ids)`: today's dedupe by `(item_id, day)` and the upsert, with `user_id` added to the values and to the `SET` list.
- `store_listings(session, user_id, rows, ids)`: `ON CONFLICT DO NOTHING` on the new key.
- Every market read starts from one CTE, `days AS (SELECT * FROM market_day)`. This is the seam for per-user rows later (ADR-0011).

### Inventory import

- `archebag.py` holds today's `inventory/csv_format.py`. Every filled slot yields `ItemFacts(name, category, npc_price, captured_at)`.
- `store_snapshots(session, user_id, snaps)` holds today's `_import_place` and `_save_chest_names`, with these changes:
  - it starts with `SELECT pg_advisory_xact_lock(hashtextextended(:user_id, 0))`;
  - slots carry `item_id`;
  - chest snapshots store `character = ''` and the saver in `saved_by`.
- Grid reads join `item` for the name, grade and category, whether the item is verified or not.

### Logging (`core/logging.py`)

```python
request_id: ContextVar[str]               # default "-"
def configure_logging(level: str) -> None # root handler -> stdout, JSON; called in main.py and cli.py
def get_logger(name: str) -> EventLogger  # .debug/.info/.warning/.error/.exception(event, **fields)
class RequestIdMiddleware                  # pure ASGI
```

- **Line format:** `{"ts","level","module","event","request_id", **fields}`, with exceptions under `exc`.
- **Third-party loggers** go through the same handler.
- **`RequestIdMiddleware`** keeps `X-Request-ID` when it matches `[A-Za-z0-9-]{1,64}`, else uses `uuid4().hex`. It echoes the header and logs one `http.request` line with method, path, status and ms. Uvicorn runs with `--no-access-log`.
- **Event names** follow `module.verb`: `import.done`, `icons.fetch_failed`, `auth.oauth_failed`, `http.request`.
- **Where it replaces old code:** `icons.py` and `oauth.py` switch from `logging.getLogger`. The CLI's `print` stays, because it is the command's reply, not a log.
- **Privacy:** log fields never carry character names or emails.

### "All my items" (`GET /api/inventory/items`)

There are 2 queries whatever the number of places, and the frontend does the search and the category filter:

```sql
WITH newest AS (
  SELECT DISTINCT ON (container, chest, character) id, container, chest, character, saved_by
  FROM inventory_snapshot WHERE user_id = :user_id
  ORDER BY container, chest, character, captured_at DESC, snapshot_id DESC)
SELECT i.id, i.name, i.item_type, i.grade, i.category, i.verified,
       n.container, n.chest, n.character, n.saved_by, sum(s.count) AS count
FROM newest n JOIN inventory_slot s ON s.snapshot = n.id AND s.item_id IS NOT NULL
JOIN item i ON i.id = s.item_id
GROUP BY i.id, n.container, n.chest, n.character, n.saved_by;
-- query 2: SELECT chest, name FROM inventory_chest_name WHERE user_id = :user_id
```

Python folds the rows per item into `{item…, total, places: [{container, character, chest, saved_by, count}]}`, sorted by name.

### Market reads for option A

**`GET /api/market/items`** is one query over every item with market days or listings. It returns:
- `id`, `name`, `item_type`, `grade`;
- `category`, which falls back to a sibling grade of the same type when NULL;
- `last_day`;
- `min_stack = max(10, ceil(0.002 × avg daily volume of the 7 days before last_day))`;
- `cheapest_real`, the lowest `unit_price` of an `ok` row with `stack ≥ min_stack` in the item's newest scan, which is the newest by `captured_at`;
- `scan_at`.

**`GET /api/market/items/{id}/listings`** returns `{scan_id, captured_at, min_stack, listings: [… , tiny]}` for the item's newest scan. The `min_stack` formula lives in one Python helper that both queries use.

**`GET /api/market/items/{id}/days`** is unchanged apart from the `days` CTE. The header tiles come from it:
- avg today = `daily_avg` of the last day;
- 7-day avg = the `weekly_avg` of the day before;
- sold today / avg = the last day's `volume` against the mean of the 7 days before.

**`/summary` is removed.**

The tree has one node per item type. The Grade select switches between that type's items. Grades that the addon did not search show offers and an empty chart.

## API

| Endpoint | Change |
|---|---|
| `POST /api/import` | + `run_id` per file; V2 headers accepted next to V1 |
| `GET /api/market/items` | new fields as above; `item_type` and `grade` are non-null; `item_grade` becomes `grade` |
| `GET /api/market/items/{id}/listings` | becomes an object with `min_stack` and `tiny` per row |
| `GET /api/market/items/{id}/days` | unchanged |
| `GET /api/market/summary` | removed |
| `GET /api/inventory/characters`, `/chests` | same shape; slot fields come from `item`, plus `item_id`, `category`; `saved_by` from its column |
| `GET /api/inventory/items` | new |
| `GET /api/inventory/icons/{item_type}.png` | unchanged |
| `/admin` | `Item` is editable; `Import runs` and `Import issues` are read-only |

## Frontend

- `lib/core/api.d.ts` is regenerated, and `types.ts` re-exports the new types.
- `lib/market/`:
  - `tree.ts` (pure): category → item type → grades, the search filter, short prices, and the tiles from days;
  - `CategoryTree`, `OffersTable` (from `ListingsTable`, with the tiny badge), and `MarketChart` with `chart.ts` restyled to the game look at a fixed aspect;
  - `SummaryTable` and `fetchSummary` are removed;
  - `routes/market` is rebuilt to option A.
- `lib/inventory/`:
  - `fetchAllItems()`;
  - `owned.ts` (pure): search, the category filter, and place labels through `chestLabel` and `chestOwner`;
  - `OwnedTable`;
  - a new `routes/items/all`, linked from `/items`.
- `routes/import` shows `run_id`.

## Build order

Each step is one branch and one PR, and each leaves the app working and CI green. Plans are written per step, after the previous step merges.

1. **Technical logging:** `core/logging.py`, the middleware, `--no-access-log`, and the switch of the current loggers. Builds ADR-0010, technical layer.
2. **Connectors, same behaviour:** move both `csv_format.py` files and the import halves of the services into `imports/`, and move `GAME_TZ` to `core/time.py`. Today's import tests must pass with behaviour unchanged. Builds ADR-0009 and ADR-0012.
3. **Item base:**
   - the fresh baseline and `items/`;
   - `resolve` with verification;
   - the uploader on market rows;
   - slots pointing at `item_id`;
   - the chest place key;
   - `import_run` and `import_issue` with the admin views;
   - the V2 headers.

   Then `make dev-reset`, the seed and a re-import. Builds ADR-0007, ADR-0008, ADR-0010 (business layer) and ADR-0011.
4. **All my items:** the endpoint with a query-count test, and the page.
5. **Market option A:** the reads and the page. This step needs the ArcheMarket 7e files.

## Review focus

The input classes the tests must pin, most likely first:
1. A player and an admin upload the same new item at the same time. It must end verified, with exactly one row.
2. An old file is uploaded after a newer one. No item field, market day or snapshot goes back.
3. A player file names a verified item with a different name or a category to fill. The item stays as it was and one `item_mismatch` is logged.
4. A V2 listings page holds offers of two grades of one name. Each row goes to its own item, and `cheapest_real` is per item.
5. An account with 5 characters and 10 chests. "All my items" still runs 2 queries, and grids show unverified items normally.

## Left to the builder

- The exact file split inside `imports/` beyond the files named above.
- The query-count helper used in tests (a SQLAlchemy `before_cursor_execute` counter).
- Whether `ImportIssueAdmin` links from a run to its issues or only filters by `run_id`.
