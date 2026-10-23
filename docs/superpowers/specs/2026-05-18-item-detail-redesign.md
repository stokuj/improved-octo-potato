# Spec: Item Detail Page Redesign

**Date:** 2026-05-18
**Scope:** `/items/[id]` — full page redesign (layout, chart, recipe tree)
**Reference:** `design_handoff_item_detail/` — Layout B+, Nested Recipes "Tree + buy/craft toggle"

---

## Goal

Replace the current tabbed layout (Price History tab | Crafting tab) with a persistent two-column view where chart and recipe tree are always visible simultaneously. Elevate profit-per-craft to a hero element. Make the recipe tree navigable to 5 levels with per-node buy/craft mode switching.

---

## Layout

### Desktop (≥1024px)

```
┌─ top bar (full width) ──────────────────────────────────────┐
│ ← Back to items                    7D  30D  90D  MAX        │
└─────────────────────────────────────────────────────────────┘
┌─ left 32% ──────────┐  ┌─ right 68% ──────────────────────┐
│ Identity card        │  │ Price history card               │
│ Profit hero card     │  │ Recipe card                      │
│ Price card           │  │                                  │
│ Actions card         │  │                                  │
└──────────────────────┘  └──────────────────────────────────┘
```

Grid: `grid lg:grid-cols-[32%_1fr] gap-3`

### Mobile (<1024px)

Single column, order: identity → profit hero → price → chart → recipe → actions (sticky bottom bar).

---

## Components

New components to create:

| Component | Path | Responsibility |
|---|---|---|
| `ItemDetailLayout.svelte` | `routes/items/[id]/` | top-level grid, date range state |
| `IdentityCard.svelte` | `lib/components/item/` | name, pills, meta |
| `ProfitHeroCard.svelte` | `lib/components/item/` | profit value, margin bar |
| `PriceCard.svelte` | `lib/components/item/` | market price, delta |
| `ActionsCard.svelte` | `lib/components/item/` | follow button, links |
| `PriceChartCard.svelte` | `lib/components/item/` | ECharts + reference line |
| `RecipeCard.svelte` | `lib/components/crafting/` | header, stepper, modal trigger, tree, footer, warnings |
| `RecipeTree.svelte` | `lib/components/crafting/` | recursive tree render |
| `InventoryModal.svelte` | `lib/components/crafting/` | flat ingredient list + inputs |

Existing `CraftingTab.svelte` → deleted after migration.

---

## Left Column Cards

### Identity card
- Item name: `text-2xl font-bold`
- Pills: `category` + `grade` using DaisyUI badge colors
- Meta: `updated X ago` — 10px mono muted, below name

### Profit hero card
- Background: `bg-warning/15` (amber tint, DaisyUI night theme)
- Label: `PROFIT / CRAFT` — 10px mono uppercase muted
- Value: `~40px font-black text-warning` (accent reserved exclusively for profit)
- Sub-line: `margin X% · sell Yg · cost Zg` — 13px muted
- Progress bar: margin % filled, `bg-warning`
- No recipe / no prices → grey placeholder `—`

### Price card
- Market price: `text-2xl font-bold tabular-nums`
- 7D delta: `+X%` green / `-X%` red, right-aligned
- Meta: `last updated X ago` — 10px mono muted

### Actions card
- Dashed border (`border-dashed`)
- `★ Follow` — `btn btn-primary`, optimistic update (matches existing ItemTable behavior: 201 first, 204 if already followed)
- No other actions in MVP

---

## Price Chart Card

- Title: "Price history" + pill `▲ above mat. cost` (green) or `▼ below mat. cost` (red)
  - Pill only shown when recipe exists and `material_cost` is computable
  - Computed from `current_price` vs `material_cost` from recipe calculate endpoint
- ECharts line chart, `min-h-[320px]`
- **Reference line:** horizontal dashed red `markLine` at `material_cost` value
  - Hidden when no recipe or no prices
- **Tooltip:** date + price + `profit = price − mat_cost` (green if >0, red if ≤0)
- **Legend:** `— price · - - mat. cost`
- **Date range:** `7D | 30D | 90D | MAX` buttons in top bar control `?days=` param
  - Re-fetches price series on change, ECharts `setOption` with animation 300ms
  - Default: `30D`
  - Backend takes `from`/`to` datetime params — frontend computes `from = now − N days`

---

## Recipe Card

### Header
- Title: "Recipe"
- Right side: batch size stepper `− [N] +` (min 1, max 999, no reload — reactive) + `edit inventory ✎` link

### Inventory Modal
- Trigger: `edit inventory ✎` link
- Content: flat list of all unique raw/leaf ingredients in tree, `<input type="number">` per item
- Storage: `localStorage` keyed by `item_id` → `{ [ingredient_item_id]: number }`
- On close: recipe tree recomputes `still_need = max(0, need − have)` reactively

### Recipe Tree Table

Columns:

| Col | Width | Content |
|---|---|---|
| Depth bar | 4px | Solid color bar, color per depth level |
| Ingredient | flex | `[toggle] [indent] [name] [level chip]` |
| Need | 70px | qty × batchSize, right-aligned tabular-nums |
| Unit | 90px | unit market price, mono |
| Mode | 90px | pill — see Mode pills below |
| Subtotal | 100px | Need × Unit, bold, right-aligned |

**Depth colors:**
- L0: `#1a1a1a` (root / target item)
- L1: `#3554c8` (blue)
- L2: `#1f8a5b` (green)
- L3: `#b5701b` (amber)
- L4: `#8a3b6b` (purple)
- L5: `#7a786f` (muted)

**Indent:** `padding-left: depth × 18px`, max 90px total.

**Toggle column:**
- `▾` — expanded (has children, currently open)
- `▸` — collapsed (has children, currently closed). Shows `+N deeper` hint next to name.
- `·` — leaf node (disabled, dashed border)

**Mode pills:**
- `raw` — grey, non-interactive (leaf, no recipe)
- `craft` — amber, clickable → switches to `buy`
- `buy @ market` — green, clickable → switches back to `craft`. Sub-tree dimmed (`opacity-40`), node uses `current_price × qty` instead of computed cost.
- `labour` — blue, non-interactive

**Expand presets toolbar** (top-right of recipe card): `L1 | L2 | L3 | all`
- Default: L2
- Persisted to `sessionStorage`

**Sticky footer:**
- `Total material cost` label + value `~30px font-black tabular-nums`
- `profit / margin` below in green (>0) or red (≤0)
- Summary: `N raw items · M bought at market · P labour`

**Inline warnings** (below table, above footer):
- One line per warning, `·` prefix, 11px mono muted
- `why?` link opens tooltip
- Example: `· Rainbow Polish has 1 price source (low confidence) — why?`
- Not a full-width banner

---

## State

Per page session (Svelte 5 `$state`):

```js
dateRange        // '7D' | '30D' | '90D' | 'MAX', default '30D'
batchSize        // number, default 1
nodeOverrides    // Record<itemId, { mode: 'craft' | 'buy', expanded: boolean }>
expandPreset     // 'L1' | 'L2' | 'L3' | 'all', default 'L2'
```

Persisted to `localStorage`:
```js
inventory        // Record<itemId, number> — keyed by page item_id
```

Derived (computed from above):
```js
materialCost     // sum of subtotals respecting nodeOverrides
profit           // current_price × output_qty − materialCost
margin           // profit / (current_price × output_qty)
flatRaws         // for warnings (items with 1 price source, etc.)
```

---

## Backend API

No new endpoints. Uses existing:
- `GET /api/items/{id}` — item data
- `GET /api/items/{id}/prices?source=ah&days=30` — price series for chart
- `POST /api/crafting/{id}/calculate` — recipe tree with `multiplier` + `inventory`
- `POST /api/user-items/{id}` — follow (idempotent: 201 / 204)

`material_cost` and `profit` are computed client-side from the tree to support reactive batch size and node overrides without round-trips.

---

## What is Removed

- `tabs tabs-bordered` (Price History / Crafting) — deleted
- Per-row `Have: 0` inputs in crafting table — replaced by inventory modal
- `¤` currency symbol — replaced by gold/silver/copper formatting matching rest of app
- ALL CAPS labels (`CURRENT PRICE`, `UPDATED:`) — replaced by 10px mono muted meta tags
- Full-width yellow warning banner — replaced by inline mono warnings

---

## Out of Scope

- Shopping list view (flat raw materials)
- Cost flow / waterfall view
- Mobile drill-down view (tree collapses to flat on mobile instead)
- User recipe overrides (local recipes per user)
