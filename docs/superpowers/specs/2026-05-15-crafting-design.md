# Crafting System — Design

## Overview

Add crafting recipes to items and a calculator that computes material costs, profit margins, and craftability given an optional user inventory. Recipes are loaded via manual SQL (from Google Docs). No UI for recipe management.

## Architecture

New domain `app/crafting/` following the existing pattern, with a dedicated `calculator.py` for the recursive tree logic:

```
app/crafting/
  models.py      # Recipe, RecipeIngredient
  schemas.py     # CraftNode, CraftSummary, CalculateRequest
  services.py    # CRUD — fetch recipes, list summaries
  calculator.py  # build_craft_tree() — recursive, cycle detection
  router.py      # GET /api/crafting/, POST /api/crafting/{item_id}/calculate
  admin.py       # ModelAdmin for Recipe and RecipeIngredient
```

## Data Model

```
Recipe
  id: int PK
  item_id: int FK → Item  (unique — one recipe per item)
  output_qty: int          (how many units one craft produces)

RecipeIngredient
  id: int PK
  recipe_id: int FK → Recipe
  ingredient_item_id: int FK → Item
  quantity: int            (needed per one craft)
  UNIQUE (recipe_id, ingredient_item_id)
```

Both models registered in sqladmin for read-only inspection after SQL import.

## API

### `GET /api/crafting/`

Returns all recipes with pre-calculated margin summary. No pagination.

```json
[
  {
    "item_id": 21,
    "item_name": "Blazing Sword",
    "output_qty": 1,
    "total_material_cost": 240000,
    "market_price": 280000,
    "profit_per_craft": 40000
  }
]
```

`profit_per_craft = market_price * output_qty - total_material_cost`. Null if `market_price` is null.

### `POST /api/crafting/{item_id}/calculate`

Request body:
```json
{
  "multiplier": 10,
  "inventory": { "42": 6000, "17": 200 }
}
```

`multiplier` defaults to 1. `inventory` defaults to `{}`.

Response — root `CraftNode` plus summary fields:
```json
{
  "item_id": 21,
  "item_name": "Blazing Sword",
  "output_qty": 1,
  "multiplier": 10,
  "market_price": 280000,
  "profit_per_craft": 40000,
  "ingredients": [
    {
      "item_id": 42,
      "item_name": "Iron Ingot",
      "qty_needed": 1200,
      "unit_price": 1200,
      "total_cost": 1440000,
      "can_craft": false,
      "crafts_possible": 5,
      "ingredients": []
    }
  ],
  "total_material_cost": 2400000
}
```

**Errors:**
- `404` — item has no recipe
- `400` — cycle detected (message names the offending item) or depth > 10

## Calculator Logic (`calculator.py`)

`build_craft_tree(item_id, multiplier, inventory, all_recipes)`:

1. Load all recipes in one query before recursion: `{item_id: Recipe}` dict — avoids N+1
2. Recurse with `visited: set[int]` (cycle detection) and `depth: int` (limit 10)
3. `qty_needed` at each node = ingredient quantity × multiplier (multiplier applied once at root level; child quantities already account for parent's qty_needed)
4. `crafts_possible = floor(inventory.get(item_id, 0) / qty_needed)` if inventory provided, else `null`
5. `total_cost = qty_needed * (item.current_price or 0)`
6. `can_craft = item_id in all_recipes`
7. Leaf nodes (no recipe): `ingredients = []`, `can_craft = false`

`GET /api/crafting/` reuses `build_craft_tree` with `multiplier=1, inventory={}` for each item that has a recipe, returns only summary fields.

## Frontend

New tab **"Crafting"** on `/items/[id]`, visible only when item has a recipe. Checked via `GET /api/crafting/{item_id}/calculate` response (404 = no recipe).

**UI layout:**
- Global multiplier input (number, default 1) + "Calculate" button
- Ingredient tree — each row:
  ```
  [+/-] Iron Ingot   need: 1,200   have: [____]   unit: 1,200 ¤   total: 1,440,000 ¤
  ```
  - `+` toggle only if `can_craft: true` (has sub-recipe)
  - `have` input feeds into `inventory` map on next Calculate call
- Summary bar: **Total cost / Market price / Profit per craft**

**Svelte state:**
- `craftTree` — full response from calculate
- `inventory: Record<number, number>` — user-entered quantities per item_id
- `multiplier: number`
- `expanded: Set<number>` — which sub-recipes are expanded

## Migration

New Alembic migration adding `recipe` and `recipeingredient` tables. Both models imported in `alembic/env.py`.

## Future: Per-User Inventory (v2)

`inventory` is already a plain request-body map `{item_id: qty}`. To add persistence:
1. Add `UserInventory(user_id, item_id, quantity)` table
2. Pre-populate the `inventory` map from DB before calling `build_craft_tree`
3. No changes to calculator logic or schemas required
