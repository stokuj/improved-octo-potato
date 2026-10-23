# Spec: User Inventory

**Date:** 2026-05-19
**Scope:** Per-user item quantity storage in DB, `/inventory` management page, RecipeTree pre-fill

---

## Goal

Logged-in users can store item quantities (their in-game inventory) in the database. This data pre-fills the "Have" column in the recipe tree so crafting cost calculations are accurate without manual entry on each visit. Non-logged-in users see an empty "Have" column with no persistence.

---

## Database

New table `user_inventory`:

```
user_id   UUID  FK → user.id   NOT NULL
item_id   int   FK → item.id   NOT NULL
quantity  int   ≥ 0            NOT NULL
PK: (user_id, item_id)
```

`quantity=0` rows are deleted — a missing row means quantity=0. Same pattern as `UserItem`.

Module: `backend/app/user_inventory/` — models.py, schemas.py, services.py, router.py (no admin needed).

---

## API

All endpoints require authentication (JWT cookie). Unauthenticated requests → 401.

### `GET /api/inventory`
Returns the full inventory for the current user.

Response: `list[InventoryItem]`
```json
[
  { "item_id": 1, "item_name": "Iron Ore", "category": "Crafting", "grade": "Basic", "quantity": 500 },
  ...
]
```
Only rows where quantity > 0 are returned. Items with no row → quantity 0.

### `PUT /api/inventory/{item_id}`
Set quantity for one item. Upserts the row; deletes if quantity=0.

Body: `{ "quantity": 500 }` — validated `ge=0`.

Response: `204 No Content`

### `GET /api/inventory/for-recipe/{item_id}`
Returns inventory quantities for all ingredients appearing in the full recipe tree of the given item (all depths, recursively). Used by the item detail page to pre-fill "Have" without loading the full inventory.

Response: `Record<int, int>` — `{ item_id: quantity, ... }` (only items in the recipe tree with quantity > 0)

Returns `{}` if the item has no recipe.

---

## Frontend — `/inventory` page

New route: `frontend/src/routes/inventory/+page.svelte`

**Access:** Visible in navbar only when logged in. Redirects to `/auth` if accessed while logged out.

**Layout:**
- Sticky filter bar (same style as `/items`): text search + category dropdown + grade dropdown
- Table below showing **all items from the DB** (not just those with quantity > 0)

**Table columns:** Name | Category | Grade | Quantity (input)

**Behavior:**
- Quantity input: `type="number" min="0"`, debounced 400ms → `PUT /api/inventory/{item_id}`
- Input value `""` or `0` → sends `quantity: 0` → backend deletes the row
- Items with no inventory row show empty input (placeholder "0")
- Filtering/search is client-side over the full item list fetched once on mount
- No "Save all" button — auto-save per field

**Data loading:** `GET /api/items?limit=1000` (all items) + `GET /api/inventory` on mount, merged client-side.

---

## Frontend — RecipeTree integration

In `+page.svelte` for `/items/[id]`:

### Logged in
- `loadCraftTree()` calls `GET /api/inventory/for-recipe/{item_id}` in parallel with the craft tree fetch
- Result replaces `inventory` state (was localStorage)
- "Have" column pre-filled from DB
- `handleSetInventory(itemId, value)` calls `PUT /api/inventory/{itemId}` instead of writing to localStorage

### Not logged in
- `GET /api/inventory/for-recipe/{item_id}` returns 401 → `inventory = {}`
- "Have" column is empty, changes are not persisted anywhere
- localStorage is removed entirely (no fallback)

**Auth check:** Use existing `$auth` state from `src/lib/auth.svelte.js` to determine whether to attempt the inventory fetch.

---

## What is removed

- `localStorage` inventory from `+page.svelte` (`localStorage.getItem/setItem/removeItem` calls)
- `handleInventoryUpdate` function (replaced by per-item `PUT` calls)

---

## Out of scope

- Bulk import/export of inventory
- Inventory value display (quantity × price)
- Inventory for non-logged-in users
- "Plan a craft" (deduct from inventory on craft)
