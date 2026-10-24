# Market Auction House (PR 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two changes in one PR:
- the app accepts ArcheMarket 7e files;
- `/market` becomes the in-game-style Auction House (option A): a category tree, the offers of the selected item, and a Prices chart like the game's.

**Architecture:**
- **Parser.** `market/csv_format.py` learns the two 7e headers next to the old ones.
- **Import.**
  - Offer rows with `item_type,item_grade` resolve items by type + grade, like market rows.
  - `market.csv` writes the game's `category` to a new nullable `item.category` column (migration `0005`).
- **Reads.**
  - `GET /market/items` grows into the one call that feeds the tree: it adds `category`, `min_stack`, `cheapest_real` and `scan_at`.
  - Listings come back with `min_stack` and a `tiny` flag.
  - `/summary` is removed.
- **Frontend.**
  - Pure helpers in `lib/market/tree.ts`.
  - A restyled ECharts builder in `chart.ts`.
  - New components: `CategoryTree`, `OffersTable` and `ItemIcon`.
  - A rebuilt `routes/market/+page.svelte`.

**Tech Stack:** FastAPI + SQLModel + Postgres 16, Alembic; SvelteKit 2 (Svelte 5 runes), DaisyUI 5 (light theme), Tailwind 4, ECharts 6 (SVG renderer), vitest, Playwright.

**Spec:**
- `docs/superpowers/specs/2026-10-23-market-auction-house-design.md`: page, chart and rules;
- `docs/superpowers/specs/2026-10-23-item-base-architecture-design.md`, section "Market reads for option A": endpoint shapes;
- addon contract: ArcheMarket `llm-wiki/project/step7e-design.md`.

**Branch:** `feature/market-auction-house` from `main` (already created).

## Global Constraints

**Headers**, exact:
- `LISTINGS_HEADER_V2 = LISTINGS_HEADER + ",item_type,item_grade"`;
- `MARKET_HEADER_V2 = MARKET_HEADER + ",category"`.

The old headers stay accepted.

**What PR 1 builds now, and what waits for PR 2** (the item base, ADR-0007/0008):
- `UNIQUE(name)` on `item` stays until PR 2. Two grades of one name in one file are therefore a row error with the existing `GRADE_CONFLICT` reason.
- Because names stay unique, two grades cannot share a name yet. The read-time category fallback to a sibling grade therefore also waits for PR 2.
- `MarketItemRead` keeps the field name `item_grade`. The rename to `grade` comes with the column rename in PR 2.

**Tiny-stack rule** (spec): `min_stack = max(10, ceil(0.002 × avg daily volume of the 7 days before the item's last day))`.
- The 0.2 % is a fraction, not a percentage.
- No history means `min_stack = 10`.
- A listing is `tiny` when `status == "ok"` and `stack < min_stack`.
- `cheapest_real` is the lowest `unit_price` among `ok` rows of the newest scan with `stack >= min_stack`, or `null`.

**Newest scan of an item:** `max(scan_id)` (`scan_id` is epoch seconds), as today.

**Chart colours** (spec):
- 7-day averages: `#e8862a`, line width 3.5;
- Same-day averages: `#22b89a`, line width 2;
- Volume: `#6c6fb3`;
- today shade: `rgba(120,180,160,.18)`;
- grid lines: `#d9d6cc`;
- box background: `#faf8f3`;
- today's date label: the theme primary `#422ad5`.

No point markers.

**Chart shape:** it keeps its aspect ratio, `aspect-ratio: 25 / 14`, so a wider column makes it taller, never flat. The price panel is about 0.30 × width and the volume panel about 0.14 × width.

**Copy:**
- Toolbar: `Grade`, `Search items…`, `Sort` with `Unit price ↑` (default), `Unit price ↓` and `Stack size ↓`.
- Offers: `Offers now`, `tiny stack`.
- Prices: `Prices`, `7 days`, `14 days`.
- Header tiles: `Cheapest real offer`, `Avg today`, `Sold today / avg`.
- Items without a category go under `Other`.
- The offers table has no "vs 7-day avg" column, and the page has no fourth "Today vs last 7 days" column (the user removed both).

**Look:**
- The app's DaisyUI light theme and its existing components (`card`, `select`, `input`, `badge`, `join`, `table`); only the chart copies the game.
- Money is always `formatCurrency`.
- Icons and grade frames reuse `iconUrl`, `gradeFrame` and `gradeName` from `lib/inventory`.

**Rules:**
- No new dependencies.
- Never dual axes: price and volume are two panels.
- Never a real character name in fixtures or docs.
- Every new non-route file starts with a one-line reason comment.

**Commands:**
- Backend tests: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest …`. Start a throwaway Postgres first: `docker run -d --rm --name octo-test-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16`.
- Frontend: `cd frontend && npx vitest run …`, `npm run check`.

## Review Focus

1. **Old-header files** (the current fixtures, files already on disk) import exactly as before: the same counts, the sum rule, and re-upload is a no-op. Pinned in Task 2.
2. **A V2 listings file with two grades of one name.** The first grade imports, the other grade's rows are row errors with `GRADE_CONFLICT`, and the sum rule holds. Nothing is silently merged. Pinned in Task 2.
3. **An item with listings but no market days.** It is in the tree with `min_stack = 10` and `cheapest_real` from its stacks ≥ 10, and the page shows "No market data" instead of a chart. Pinned in Tasks 3 and 6.
4. **The newest scan has only status rows** (`no_result`). `cheapest_real` is null, the tree shows `—`, and the offers card shows the status word. Pinned in Tasks 3 and 6.
5. **A search with no matches.** The tree says `No items match`, and the selected item's offers and chart stay on screen. Pinned in Tasks 4 and 6.

---

### Task 1: Parse the 7e headers

**Files:**
- Modify: `backend/app/market/csv_format.py`
- Test: `backend/tests/market/test_csv_format.py`

**Interfaces:**
- Produces:
  - `LISTINGS_HEADER_V2`, `MARKET_HEADER_V2` (exact strings as in Global Constraints);
  - `ListingRow` gains `item_type: int | None = None` and `item_grade: int | None = None`, appended at the end;
  - `MarketRow` gains `category: str | None = None`, appended at the end;
  - `CATEGORY_MAX = 64`.

Rules for the new columns:
- In a listings V2 row, the type and grade are either both integers (a key) or both empty (no key). One set without the other is the row error `item_type and item_grade must both be set or both empty`.
- A status row (`rank` 0) must have both empty, or it is the row error `<status> row needs empty item_type and item_grade`.
- In a market V2 row, `category` is the string, with `""` read as `None`. A category longer than 64 is the row error `category longer than 64`.
- Widths are 8 / 10 for listings and 12 / 13 for market, chosen by header.

- [ ] **Step 1: Write the failing tests**

```python
def test_listings_v2_reads_type_and_grade():
    data = (LISTINGS_HEADER_V2 + "\n1,1,Leather,ok,1,4650,2418000,520,16327,0\n"
            "1,1,Leather,no_result,0,,,,,\n").encode()
    p = parse_csv(data)
    assert p.kind == "listings" and not p.errors
    assert (p.listings[0].item_type, p.listings[0].item_grade) == (16327, 0)
    assert (p.listings[1].item_type, p.listings[1].item_grade) == (None, None)

@pytest.mark.parametrize("tail, reason", [
    ("16327,", "item_type and item_grade must both be set or both empty"),
    (",0", "item_type and item_grade must both be set or both empty"),
])
def test_listings_v2_half_key_is_row_error(tail, reason):
    p = parse_csv(f"{LISTINGS_HEADER_V2}\n1,1,Leather,ok,1,4650,2418000,520,{tail}\n".encode())
    assert [e.reason for e in p.errors] == [reason]

def test_listings_v2_status_row_with_key_is_row_error():
    p = parse_csv(f"{LISTINGS_HEADER_V2}\n1,1,Leather,no_result,0,,,,16327,0\n".encode())
    assert [e.reason for e in p.errors] == ["no_result row needs empty item_type and item_grade"]

def test_market_v2_reads_category_and_empty_is_none():
    rows = "\n".join(f"1792607894,1792607894,Leather,16327,0,ok,{d},4702,4877,2100,19999,1000,{c}"
                     for d, c in ((14, "Hide"), (13, "")))
    p = parse_csv(f"{MARKET_HEADER_V2}\n{rows}\n".encode())
    assert [m.category for m in p.market] == ["Hide", None]

def test_market_v2_category_too_long_is_row_error():
    p = parse_csv(f"{MARKET_HEADER_V2}\n1,1,Leather,16327,0,ok,14,1,1,1,1,1,{'x' * 65}\n".encode())
    assert [e.reason for e in p.errors] == ["category longer than 64"]

def test_v1_headers_still_parse():   # the sample fixtures are V1
    assert parse_csv((FIXTURES / "listings.csv").read_bytes()).kind == "listings"
    assert parse_csv((FIXTURES / "market.csv").read_bytes()).kind == "market"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/market/test_csv_format.py -v`
Expected: FAIL with `ImportError: cannot import name 'LISTINGS_HEADER_V2'`.

- [ ] **Step 3: Implement the headers, fields and rules as in Interfaces**

- [ ] **Step 4: Run the file and the whole market folder**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/market -q`
Expected: all pass (the old tests are unchanged).

- [ ] **Step 5: Commit**: `feat(market): parse the ArcheMarket 7e headers`

### Task 2: Import V2 files: type + grade per offer, category per item

**Files:**
- Modify: `backend/app/market/models.py`: `Item.category: str | None = Field(default=None, max_length=64)`.
- Create: `backend/alembic/versions/0005_item_category.py`: add `item.category varchar(64) NULL`; the downgrade drops it.
- Modify: `backend/app/market/services.py`, `_import_listings` and `_import_market`.
- Test: `backend/tests/market/test_import.py`

**Interfaces:**
- Consumes: Task 1's `ListingRow.item_type/item_grade` and `MarketRow.category`.
- Produces: `Item.category`. `resolve_items` keeps its signature `(session, market_keys: dict[str, tuple[int, int]], listing_names: set[str])`.

How the import changes:
- **`_import_listings`**:
  - rows with a key feed `market_keys` (`setdefault(name, key)`);
  - rows without a key feed `listing_names`;
  - a keyed row whose key differs from `market_keys[name]` is a `GRADE_CONFLICT` row error, the same check `_import_market` already makes.
- **`_import_market`**: after the upsert, it sets `item.category` for each item to the category of that item's newest row (by `captured_at`) that has one. Rows without a category leave the stored value as it is. This does not touch the counts.

- [ ] **Step 1: Write the failing tests**

Build V2 files from the V1 fixtures in the test with `rewrite_fixture`, then append the columns. Helper, in `test_import.py`:

```python
def to_v2(data: bytes, extra: Callable[[dict], list[str]]) -> bytes:
    """Append V2 columns: extra(row_as_dict) returns the new cell values."""
```

Tests:

```python
async def test_v2_market_sets_category(superuser_client, session):
    s, base = uuid.uuid4().hex[:8], _base()
    data = to_v2(rewrite_fixture("market.csv", s, base), lambda r: ["Hide"])
    [r] = await upload(superuser_client, ("market.csv", data)); assert_sum(r)
    item = (await session.exec(select(Item).where(Item.name == f"Leather {s}"))).one()
    assert item.category == "Hide"

async def test_v2_market_empty_category_keeps_stored(superuser_client, session): ...
    # upload with "Hide", then the same items with "" -> still "Hide"

async def test_v2_listings_resolve_by_type_and_grade(superuser_client, session):
    # listings-only V2 upload for a new name: the item is created WITH item_type/item_grade
    ...
    assert (item.item_type, item.item_grade) == (base + 16327, 0)

async def test_v2_listings_two_grades_of_one_name(superuser_client):
    # one file: Leather <s> rank 1-2 at grade 0, rank 3 at grade 2 (same item_type)
    [r] = await upload(superuser_client, ("listings.csv", data))
    assert_sum(r)
    assert [e["reason"] for e in r["errors"]] == [services.GRADE_CONFLICT]
    assert r["inserted"] == 2

async def test_v1_listings_after_v2_market_match_by_name(superuser_client): ...
    # the existing V1 fixture uploaded after a V2 market file: same counts as test_sample_first_and_second_upload
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/market/test_import.py -k v2 -v`
Expected: FAIL. `Item` has no `category`, and the V2 listings create the item without a type.

- [ ] **Step 3: Implement the model field, the migration and the two import changes**

- [ ] **Step 4: Run all backend tests and the migration checks**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/app_test uv run alembic upgrade head && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/app_test uv run alembic check`
Expected:
- the suite is green;
- alembic prints `No new upgrade operations detected.`

If the test DB's schema was made by `create_all`, run the alembic commands against a fresh database `app_migrate` instead.

- [ ] **Step 5: Commit**: `feat(market): import 7e files, store the game's category per item`

### Task 3: Market reads for option A, drop /summary

**Files:**
- Modify: `backend/app/market/schemas.py`:
  - `MarketItemRead` + `category: str | None`, `min_stack: int`, `cheapest_real: int | None`, `scan_at: datetime | None`;
  - `ListingRead` + `tiny: bool`;
  - new `ListingsRead { scan_id: int | None, captured_at: datetime | None, min_stack: int, listings: list[ListingRead] }`;
  - delete `SummaryRow`.
- Modify: `backend/app/market/services.py`:
  - `MIN_REAL_STACK = 10`, `REAL_STACK_SHARE = 0.002`;
  - `min_stack(avg_volume: float | None) -> int`;
  - `list_items` becomes one raw-SQL query;
  - `get_latest_listings -> ListingsRead`;
  - delete `_SUMMARY_SQL` and `get_summary`.
- Modify: `backend/app/market/router.py`: `/items/{id}/listings` returns `ListingsRead`; delete `/summary`.
- Test: `backend/tests/market/test_queries.py`. Replace `test_summary_leather_matches_samples` and `test_change_pct_null_when_avg_7d_zero`, and adapt `test_listings_are_newest_scan_by_rank` and `test_listing_only_item` to the new listings shape.

**Interfaces:**
- Produces:
  - `GET /api/market/items -> list[MarketItemRead]`;
  - `GET /api/market/items/{id}/listings -> ListingsRead`;
  - `services.min_stack`.

The query for `list_items`:
- It has CTEs `last_day`, `vol` (the average volume of `day BETWEEN last_day - 7 AND last_day - 1`), `latest` (`max(scan_id)` per item) and `tracked` (the union of item ids with days or listings).
- It joins `item` and the newest scan's `listing` rows and orders by name.
- `cheapest_real` is `min(unit_price) FILTER (WHERE status = 'ok' AND stack >= greatest(:floor, ceil(coalesce(avg_volume, 0) * :share)))`, with `:floor`/`:share` bound from the two constants.
- The response's `min_stack` comes from `min_stack(avg_volume)`, so SQL and Python share one formula.

`get_latest_listings` computes `vol` for the one item the same way.

- [ ] **Step 1: Write the failing tests**

Build the data with a small in-test V2 builder that uses unique names and types:

```python
def v2_market(name: str, item_type: int, category: str, volumes: list[int], captured_at: int) -> bytes:
    """One row per day, oldest first, ending at day 14; daily/weekly avg 5000."""

def v2_listings(name: str, item_type: int, offers: list[tuple[int, int]], captured_at: int) -> bytes:
    """offers = [(stack, unit_price), …] as ranks 1..n, grade 0."""
```

Tests:

```python
async def test_items_carry_category_min_stack_and_cheapest_real(client, session):
    # 7 days of 100_000 then today 5_000 -> avg 100_000 -> min_stack 200
    # offers (2, 2165), (150, 4000), (520, 4965) -> cheapest_real 4965
    row = next(i for i in (await client.get("/api/market/items")).json() if i["name"] == name)
    assert (row["category"], row["min_stack"], row["cheapest_real"]) == ("Hide", 200, 4965)
    assert row["scan_at"] is not None

async def test_min_stack_floor_without_history(client, session):
    # listings only: (5, 100), (12, 300) -> min_stack 10, cheapest_real 300
    ...

async def test_only_status_rows_means_no_cheapest_real(client, session):
    # newest scan holds one no_result row -> cheapest_real None
    ...

async def test_listings_mark_tiny_and_carry_min_stack(client, session):
    body = (await client.get(f"/api/market/items/{item_id}/listings")).json()
    assert body["min_stack"] == 200
    assert [(l["stack"], l["tiny"]) for l in body["listings"]] == [(2, True), (150, True), (520, False)]

async def test_summary_is_gone(client):
    assert (await client.get("/api/market/summary")).status_code == 404

def test_min_stack_formula():
    assert [min_stack(v) for v in (None, 0, 4_999, 5_001, 100_000)] == [10, 10, 10, 11, 200]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/market/test_queries.py -v`
Expected: FAIL with `KeyError: 'category'`, `ImportError: min_stack`, and a 200 from `/summary`.

- [ ] **Step 3: Implement the schemas, services and router as in Interfaces**

- [ ] **Step 4: Run all backend tests and lint**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: green and clean.

- [ ] **Step 5: Commit**: `feat(market): one item list for the tree, tiny offers, drop /summary`

### Task 4: Frontend data layer: types, API, tree helpers

**Files:**
- Modify: `frontend/src/lib/core/api.d.ts`, regenerated as in `CLAUDE.md`.
- Modify: `frontend/src/lib/core/types.ts`: add `ListingsRead`; delete `SummaryRow`.
- Modify: `frontend/src/lib/market/api.ts`: `fetchListings(itemId): Promise<ListingsRead>`; delete `fetchSummary`.
- Create: `frontend/src/lib/market/tree.ts`
- Test: `frontend/src/lib/market/tree.test.ts`

**Interfaces:**
- Produces, all from `tree.ts`:
  - `type TreeNode = { key: string; name: string; items: MarketItemRead[] }`: one node per `item_type`, or per `id` when `item_type` is null; `items` sorted by `item_grade`; `name` is the name of `items[0]`.
  - `type TreeCategory = { name: string; nodes: TreeNode[] }`
  - `buildTree(items: MarketItemRead[], query: string): TreeCategory[]`:
    - a node's category is the first non-null `category` among its items, else `Other`;
    - categories are sorted A→Z with `Other` last, and nodes are sorted by name;
    - `query` is trimmed and matched case-insensitively against item names; a node stays if any of its items matches;
    - empty categories are dropped.
  - `shortPrice(copper: number | null): string`: `formatCurrency` without the trailing bronze when there is gold or silver, e.g. `4965 → "49s"`, `21650 → "2g 16s"`, `65 → "65b"`, `null → "—"`.
  - `nodePrice(node: TreeNode): number | null`: the lowest non-null `cheapest_real` of the node's items.
  - `gradeSiblings(items: MarketItemRead[], item: MarketItemRead): MarketItemRead[]`: the items with the same non-null `item_type`, sorted by grade; `[item]` when `item_type` is null.
  - `tileStats(days: MarketDayRead[]): { avgToday: number | null; soldToday: number | null; avgVolume: number | null }`: the last day's `daily_avg` and `volume`, and the mean volume of the up-to-7 days before it (null when there are none).
  - `type OfferSort = 'unit-asc' | 'unit-desc' | 'stack-desc'`
  - `OFFER_SORTS: { value: OfferSort; label: string }[]` with the labels from Global Constraints.
  - `sortOffers(listings: ListingRead[], sort: OfferSort): ListingRead[]`: `ok` rows only, without mutating the input.

- [ ] **Step 1: Write the failing tests** (`tree.test.ts`)

```ts
it('groups by category, Other last, one node per item type with grades sorted', ...)
  // items: A(type 1, grade 2, 'Hide'), A(type 1, grade 0, null), B(type 2, 'Metal'), C(type null, null)
  // -> [{name:'Hide', nodes:[{name: A grade-0 name, items:[g0, g2]}]}, {name:'Metal',…}, {name:'Other', nodes:[C]}]
it('search keeps matching nodes and drops empty categories; no match gives []', ...)
it('shortPrice drops bronze only when gold or silver is shown', () =>
  expect([4965, 21650, 65, null].map(shortPrice)).toEqual(['49s', '2g 16s', '65b', '—']))
it('gradeSiblings returns same-type items by grade, or the item alone without a type', ...)
it('tileStats uses the last day and the mean of up to 7 days before it', ...)
  // days volumes [10,20,30,40,50,60,70,80,9] -> avgVolume 50 (mean of 20..80), soldToday 9
it('sortOffers keeps ok rows and sorts by the chosen key', ...)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run src/lib/market/tree.test.ts`
Expected: FAIL, because the module `./tree` cannot be found.

- [ ] **Step 3: Regenerate the types, update `types.ts` and `api.ts`, implement `tree.ts`**

- [ ] **Step 4: Run the tests and the type check**

Run: `cd frontend && npx vitest run src/lib/market/tree.test.ts && npm run check`
Expected:
- the tree tests pass;
- `svelte-check` reports errors only in the files Task 6 rewrites (`routes/market/+page.svelte`, `SummaryTable*`). Note them; do not fix them here.

- [ ] **Step 5: Commit**: `feat(market): tree, price and offer helpers for the auction house page`

### Task 5: The game-style Prices chart

**Files:**
- Modify: `frontend/src/lib/market/chart.ts`. Rewrite `buildChartOptions(days: MarketDayRead[]): EChartsOption` and keep `formatVolume`.
- Modify: `frontend/src/lib/market/MarketChart.svelte`:
  - drop the `height` prop;
  - the container is `class="w-full" style="aspect-ratio: 25 / 14"`;
  - a `ResizeObserver` on it calls `chart.resize()` instead of the window listener.
- Test: `frontend/src/lib/market/chart.test.ts`, rewritten.

**Interfaces:**
- Consumes: `formatCurrency`.
- Produces: `buildChartOptions(days)`. The same name and signature, so the component stays the same.

The option shape:
- **Grids.** Two grids, each with `show: true`, `backgroundColor: '#faf8f3'` and `borderColor: '#d9d6cc'`: the price grid at `top: '7%'`, `height: '54%'`, and the volume grid at `top: '70%'`, `height: '24%'`. Both have `left: 12` and `right: 92`.
- **x axes.** Categories are the days.
  - Axis 0 sits on top and shows labels only at index 0, `floor((n-1)/2)` and `n-1`, formatted `MM.DD`. The last label has colour `#422ad5` and weight 600.
  - Both x axes have vertical `splitLine`s (`#d9d6cc`, interval 0).
- **y axes.** Both have `position: 'right'`.
  - Price: `min: 0`, `max: ceil(1.2 × max(daily_avg, weekly_avg))`, `interval: max / 5`, labels `formatCurrency`.
  - Volume: `min: 0`, `max: max(volume)` (1 when all are 0), `interval: max / 3`, labels `toLocaleString('en-US')`.
- **Series.**
  - `7-day averages`: a line on `weekly_avg`, width 3.5, `#e8862a`.
  - `Same-day averages`: a line on `daily_avg`, width 2, `#22b89a`.
  - Both have `showSymbol: false`.
  - `Volume`: bars, `#6c6fb3`, `barWidth: '56%'`.
  - The first and last series carry a `markArea` over the last day in `rgba(120,180,160,.18)`.
- **Legends.** Two: `['7-day averages', 'Same-day averages']` at `top: '62%'` and `['Volume']` at `bottom: 0`, both left-aligned.
- **Tooltip.** On the axis, showing the date (plus ` (today, partial)` on the last day), `7-day avg`, `Same-day avg` and `Volume`, with money as `formatCurrency` and volume as `toLocaleString('en-US')`.

- [ ] **Step 1: Write the failing tests**

```ts
it('names, colours and widths follow the game', ...)        // series [name,type,color,width] as in Interfaces; no symbols
it('price axis runs from 0 to 120% of the highest average', ...) // days with weekly 1000 -> max 1200, interval 240
it('volume axis runs from 0 to the highest volume in 3 steps', ...)
it('axes sit on the right and dates show only first, middle and today', ...)
  // 14 days: axisLabel.interval(i) true only for 0, 6, 13
it('shades today in both panels', ...)                       // markArea xAxis = last day on series 0 and 2
it('tooltip marks today as partial', ...)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run src/lib/market/chart.test.ts`
Expected: FAIL, because the series names are still `Daily avg`.

- [ ] **Step 3: Rewrite `chart.ts` and `MarketChart.svelte` as in Interfaces**

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npx vitest run src/lib/market/chart.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**: `feat(market): Prices chart laid out like the game's, fixed aspect`

### Task 6: The Auction House page

**Files:**
- Create: `frontend/src/lib/market/ItemIcon.svelte`:
  - props `{ itemType: number | null; grade: number | null; size?: number (default 34); count?: number | null }`;
  - a square with a 2px grade frame (`border-image: gradeFrame(grade) 1`) on the grade's pastel colour;
  - it shows `iconUrl(itemType)` and hides it on error;
  - the count sits bottom-right through `formatCount` from `lib/inventory/grid`.
- Create: `frontend/src/lib/market/CategoryTree.svelte`:
  - props `{ tree: TreeCategory[]; selectedId: number | null; onSelect: (id: number) => void }`;
  - category headers are buttons that fold and unfold (state held in the component);
  - each leaf is a button with the node name and `shortPrice(nodePrice(node))`; it is marked `aria-current="true"` when the node holds `selectedId`;
  - clicking a leaf calls `onSelect(node.items[0].id)`;
  - an empty tree shows `No items match`.
- Create: `frontend/src/lib/market/OffersTable.svelte`:
  - props `{ data: ListingsRead; item: MarketItemRead; sort: OfferSort }`;
  - the header line reads `Scan <local time> · page 1 (top N)`, with N the `ok` rows;
  - status words show as badges, as `ListingsTable` does today;
  - columns: Name (an `ItemIcon` with the stack count, the item name, and a `badge badge-warning badge-sm` saying `tiny stack` with `title="Smaller than a useful amount: likely bait"` when `tiny`), Stack (`toLocaleString('en-US')`), Unit price and Listing price (`formatCurrency`);
  - with no rows: `No listings imported for this item yet.`
- Modify: `frontend/src/routes/market/+page.svelte`, rebuilt to option A:
  - **header:** `Market`, the selected item's `ItemIcon` (size 40), its name, `<gradeName> · <category ?? 'Other'>`, and three tiles: `Cheapest real offer` = `formatCurrency(selected.cheapest_real)`, `Avg today` = `formatCurrency(stats.avgToday)`, and `Sold today / avg` = `formatVolume(sold) / formatVolume(avg)`;
  - **toolbar:** a 3-column grid with `Grade` (a select of `gradeSiblings`, disabled when there is one, calling `select(id)` on change), a centred search input with `placeholder="Search items…"`, and `Sort` (`OFFER_SORTS`) on the right;
  - **body:** a `CategoryTree` column of 260px (280px at ≥2300px) beside a main grid. The main grid holds the `Offers now` card and the `Prices ‹grade› name` card with a `7 days | 14 days` join, and it becomes two columns (`1fr 1.1fr`) at ≥1700px and `1fr 1.4fr` at ≥2300px. Below `lg` everything stacks: tree, offers, chart.
  - Keep: `?item=` selection with the first-item fallback, the `seq` guard against stale responses, and the `Could not load …` alerts.
  - With no days, the Prices card shows `No market data for this item.`
- Delete: `frontend/src/lib/market/SummaryTable.svelte`, `SummaryTable.test.ts`, `ListingsTable.svelte`, `ListingsTable.test.ts`.
- Test:
  - `frontend/src/lib/market/OffersTable.test.ts` (new);
  - `frontend/src/lib/market/CategoryTree.test.ts` (new);
  - `frontend/src/test/routes/market.page.test.ts` (update its mocks to the new shapes, drop `/market/summary`);
  - `frontend/e2e/market.spec.ts`.

**Interfaces:**
- Consumes: Task 4's `buildTree`, `nodePrice`, `shortPrice`, `gradeSiblings`, `tileStats`, `sortOffers`, `OFFER_SORTS`, `fetchListings`; Task 5's `MarketChart`.

- [ ] **Step 1: Write the failing tests**

```ts
// OffersTable.test.ts
it('shows a tiny stack badge only on tiny rows', ...)
it('sorts by the given key and shows the scan line with top N', ...)
it('shows status words and the empty message', ...)
// CategoryTree.test.ts
it('folds a category and selects a node', ...)
it('says No items match for an empty tree', ...)
// market.page.test.ts (keep the four existing cases, adapted, plus:)
it('search filters the tree but keeps the selected item on screen', ...)
it('Grade select lists sibling grades and switches ?item=', ...)
it('listing-only item shows No market data and its cheapest real offer', ...)
```

`e2e/market.spec.ts`:
- after the import test, `/market` shows the tree, `Offers now`, and the chart SVG;
- clicking another leaf updates `?item=` and the header name;
- an anonymous visitor sees the search box but cannot import.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run src/lib/market src/test/routes/market.page.test.ts`
Expected: FAIL, because `OffersTable.svelte` and `CategoryTree.svelte` do not exist.

- [ ] **Step 3: Build the three components and the page; delete the four old files**

- [ ] **Step 4: Run everything on the frontend**

Run: `cd frontend && npx vitest run && npm run check`
Expected: all vitest green; `svelte-check` reports 0 errors.

- [ ] **Step 5: Run the page for real and look at it**

Steps:
1. Bring up the dev stack (`docker compose -p octo-dev -f infra/compose/docker-compose.dev.yml -f <override> up -d`).
2. Run the e2e suite (`make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test`).
3. Screenshot `/market` at 1900 and 2540 px wide with a throwaway Playwright script in `frontend/shot-tmp.mjs`, and delete it after.

Expected:
- e2e is green;
- at 1900 px the tree, the offers and the chart sit above the fold;
- at 2540 px the chart is taller, not flatter.

- [ ] **Step 6: Commit**: `feat(market): auction house page with category tree, offers and game-style prices`

### Task 7: Docs

**Files:**
- Add: `docs/superpowers/specs/2026-10-23-market-auction-house-design.md`. It is untracked today; commit it with these updates:
  - in "Data", mark items 1-3 as done by ArcheMarket 7e and this PR;
  - note that two grades of one name stay a row error until the item base (PR 2) drops `UNIQUE(name)`.
- Modify: `docs/superpowers/specs/2026-10-23-item-base-architecture-design.md`. In "Build order", replace the five steps with the three PRs:
  1. this PR, the 7e headers + `/market` option A;
  2. the item base (connectors + `items/` with verification, uploader, import log, fresh baseline, re-import);
  3. all my items.

  Logging (#24) is already done.
- Modify: `CLAUDE.md`:
  - the `/market` line becomes "a category tree, the cheapest offers with tiny stacks marked, and a game-style 14-day Prices chart";
  - the `lib/market/` line names `tree.ts` and the new components.
- Modify: `docs/adr/0007-item-identity-is-type-and-grade.md`, its Consequences. Add one line: until the item base lands, `UNIQUE(name)` remains and two grades of one name are a row error (ADRs may be corrected in place).

- [ ] **Step 1: Make the edits**
- [ ] **Step 2: Check the links**: `grep -rn "docs/ai" docs CLAUDE.md` prints nothing.
- [ ] **Step 3: Commit**: `docs(market): auction house spec, build order in three PRs`
