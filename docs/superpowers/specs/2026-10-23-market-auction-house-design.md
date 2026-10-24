# Market page as an Auction House — design

Status: built, 2026-10-24 (PR 1 of the item-base build order). The user picked option A out of six mockups (A–F) and approved the mockup with "ok".

Mockups:
- All six options: https://claude.ai/artifact/DxyeudZVL8wWWeCNDxqCyv
- Option A, final, with the in-game screenshots beside it and a 1900/2540 px switch: https://claude.ai/artifact/BMmehmUJEPYp26N2xwNRPF
- Local source (gitignored): `.superpowers/brainstorm/market-redesign/market-a.html`

## Intent

`/market` should work like the in-game Auction House: pick an item from a category tree, see its current offers, and see its Prices chart next to them. The user cares about how it works more than how it looks. The app keeps its own look (DaisyUI light theme, indigo primary), and only the chart copies the game.

## Layout (option A)

- **Header:** `Market`, the selected item (grade-framed icon, name, `<grade> · <category>`), and three stat tiles on the right:
  - `Cheapest real offer`;
  - `Avg today`;
  - `Sold today / avg` (for example `27k / 94k`).
- **Toolbar:**
  - left: `Grade` select;
  - centre: search box (`Search items…`) that filters the tree as you type;
  - right: `Sort` select with `Unit price ↑` (default), `Unit price ↓` and `Stack size ↓`.
- **Body, three columns:** category tree | Offers now | Prices.
  - **Tree.** The game's top categories, collapsed when they have no tracked items. Under each category, its tracked items, each with its cheapest real price in short form (`49s`). Clicking an item selects it. Categories with items fold and unfold.
  - **Offers now.**
    - Title line: `Scan <time> · page 1 (top N)`.
    - Columns: Name (grade-framed icon with the stack count on it, then the item name), Stack, Unit price, Listing price.
    - A `tiny stack` badge marks bait offers.
    - The table has **no** "vs 7-day avg" column; the user removed it.
  - **Prices:**
    - Title `Prices ‹<grade>› <item>`.
    - A `7 days | 14 days` switch.
    - The chart is described below.
- **Widths:** the page fills the screen. At 1900 px everything sits above the fold. At 2540 px the chart column takes the extra width.
  - The user **rejected** an extra fourth column ("Today vs last 7 days" for all items).
  - The current `SummaryTable` is not part of the new page.

## Chart, like the game's Prices window

- Two stacked boxes, price and volume, on a light beige background. They share one column per day.
- **The chart keeps its shape (user, 2026-10-23).** It must not stretch flat on a wide screen: as its column gets wider, it gets taller in the same proportion. The mockup uses price box height ≈ 0.30 × width and volume box height ≈ 0.14 × width, with text size unchanged.
- Axis labels are on the **right**:
  - price as money (`51s 23b`), from **0** to 120% of the highest value, 5 steps;
  - volume as full numbers (`118,365`), 0 to max, 3 steps.
- Every day has a grid cell. Today's column is shaded and its partial volume is shown as is.
- Dates are on top: first, middle and today (`10.08 … 10.14 … 10.21`), with today in the primary colour.
- Series and colours, taken from the game:
  - `7-day averages`: thick orange `#e8862a`;
  - `Same-day averages`: thin teal `#22b89a`;
  - `Volume`: purple bars `#6c6fb3`.
  - No point markers. The legend sits under each box.
- Hovering a day shows its date, both averages and the volume.
- This replaces the colours and layout of today's `lib/market/chart.ts`. The rule against dual axes still holds: these are two panels.

## Rules

- **Cheapest real offer:** the cheapest offer whose stack is at least `max(10, 0.2% of the average daily volume of the 7 days before today)`. Smaller offers get the `tiny stack` badge. The real-data sample shows why: Leather rank 1 is 2 units at 21s 65b, while the market price is about 49s 65b.
- Money is shown with `formatCurrency`. Items, icons and grades reuse `/items` pieces: `iconUrl`, `gradeFrame`, `gradeName`.
- The selected item stays in the URL (`?item=`), as today.

## Data: what exists, what is missing

Items 1–3 below are done: ArcheMarket 7e sends `category` and the offer key, and PR 1 reads both. Item 4 is done too: `GET /api/market/items` carries `cheapest_real` and `min_stack` for every item. Until the item base (PR 2) drops `UNIQUE(name)`, two grades of one name in one file stay a row error.

**Exists:**
- `GET /api/market/items`, which includes `item_type` and `item_grade`, so icons and grade frames work;
- `/items/{id}/days`;
- `/items/{id}/listings` (one page, top 9);
- `/summary` (today avg, 7-day avg, sold today, average daily volume).

**Missing:**
1. **Categories for the tree.** `market.csv` and `listings.csv` have none. ArcheBag's `inventory.csv` and `chests.csv` already carry the game's own category (`Leather → Hide`, `Lumber → Lumber`, `Iron Ingot → Metal`), so the addon API can provide it.
   - **Decided (user, 2026-10-23):** ArcheMarket adds a `category` column to `market.csv`. The app stores it per item and builds the tree from it. Items with no category go under `Other`.
   - The tree shows the game's category names as the addon sends them. Grouping them under top categories (`Crafting materials`, …) is a builder's call, and so is leaving the tree flat.
2. **Grade per listing.** `listings.csv` has no `item_type` or `item_grade`, so the Grade filter cannot work yet.
   - **Decided (user, 2026-10-23):** ArcheMarket adds `item_type` and `item_grade` to `listings.csv`, and the Grade filter works from the start.
   - Listings are then matched to items by `(item_type, item_grade)`, like market days, instead of by name.
   - The Grade select lists only the grades that occur in the item's listings.
3. **Addon contract first.** Both changes live in the ArcheMarket repo, as its next step, designed there. Until then:
   - the app keeps accepting the old headers next to the new ones;
   - an old file simply has no category and no grade.

   This is my call, not discussed with the user. The `inventory.csv` change in 7d went the other way and dropped the old header.
4. **Tree prices for all items in one call.** The tree shows each item's cheapest real price, but listings are fetched one item at a time. Extend `/summary` or add an endpoint, as long as the page does not need one request per item.

## Non-goals

- Bidding, buying, selling, or time left and partial sale per offer (the addon exports none of these).
- More than one page of offers.
- The other mockup options' features: watchlist alerts (B), Ctrl+K search (C), order-book calculator (D), heatmap (E), owned/value columns (F).
- A dark theme. `data-theme="night"` in `+layout.svelte` is not enabled in `layout.css`, so the app renders the light theme. Fixing that is a separate decision.

## Left to the builder

- Component split. `ListingsTable` and `MarketChart` can be reworked; `SummaryTable` goes away from `/market`.
- Tree state (folded categories) in memory or in `localStorage`.
- Narrow screens: the columns stack (tree, offers, chart) below about 1280 px.
- Tests: vitest for the page (tree selection, search filter, sort, tiny-stack rule, chart options) and an updated e2e market spec.
