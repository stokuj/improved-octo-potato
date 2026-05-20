# Recipe UX Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the broken Follow button, move the recipe card to full-width below the chart, replace the inventory modal with an inline "Have" column, and add a Total Labour summary to the recipe footer.

**Architecture:** Three-file frontend change — no backend, no new files. `+page.svelte` gets a layout restructure. `RecipeTree.svelte` gets a new `onSetInventory` prop and inline input column. `RecipeCard.svelte` removes the modal, wires per-item inventory updates, and adds `totalLabour` derived from the tree.

**Tech Stack:** SvelteKit 5 (runes), Tailwind CSS v4, DaisyUI.

---

## File Map

| Action | Path | What changes |
|---|---|---|
| Modify | `frontend/src/routes/items/[id]/+page.svelte` | Remove `followState`/`follow()`, restructure layout to top-grid + full-width recipe |
| Modify | `frontend/src/lib/components/crafting/RecipeTree.svelte` | Add `onSetInventory` prop, add "Have" input column between Need and Still need |
| Modify | `frontend/src/lib/components/crafting/RecipeCard.svelte` | Remove modal, remove "edit inventory" button, add `handleSetInventory`, add `totalLabour` derived, show Labour in footer |

---

## Task 1: Layout restructure + remove Follow

**Files:**
- Modify: `frontend/src/routes/items/[id]/+page.svelte`

**What changes:**
- Remove `followState` state variable and `follow()` async function
- Remove the actions card (dashed border card with Follow button)
- Change layout: top grid stays 32%/68% with info left + chart right; recipe moves below the grid at full width
- `handleSetInventory` is a new handler (needed by Task 3) — add it here so RecipeCard can use it

- [ ] **Step 1: Read the current file to confirm line numbers**

```bash
grep -n "followState\|follow()\|actions card\|grid grid-cols" /home/dv6/GitHub/improved-octo-potato/frontend/src/routes/items/[id]/+page.svelte
```

- [ ] **Step 2: Remove follow state and function from `<script>`**

In `frontend/src/routes/items/[id]/+page.svelte`, remove these lines from the script block:

```js
    /** @type {'idle'|'following'|'done'} */
    let followState = $state('idle');
```

And remove the entire `follow()` function:

```js
    async function follow() {
        if (followState !== 'idle') return;
        followState = 'following';
        try {
            await fetch(`${API_BASE_URL}/user-items/${getItemId()}`, { method: 'POST', credentials: 'include' });
            followState = 'done';
        } catch { followState = 'idle'; }
    }
```

- [ ] **Step 3: Add `handleSetInventory` to the script block**

Add this function after `handleInventoryUpdate`:

```js
    /** @param {number} itemId @param {number} value */
    function handleSetInventory(itemId, value) {
        const next = { ...inventory };
        if (value > 0) next[itemId] = value;
        else delete next[itemId];
        handleInventoryUpdate(next);
    }
```

- [ ] **Step 4: Restructure the HTML template**

Replace the entire `{:else if item}` block (currently a single `grid lg:grid-cols-[32%_1fr]`) with:

```svelte
    <!-- ── B+ layout: top = info+chart, bottom = recipe full width ── -->
    <div class="space-y-3">

        <!-- Top row: info left, chart right -->
        <div class="grid grid-cols-1 lg:grid-cols-[32%_1fr] gap-3 items-start">

            <!-- LEFT: identity + profit hero + price -->
            <div class="flex flex-col gap-3">

                <div class="card bg-base-100 border border-base-200 shadow-sm">
                    <div class="card-body p-4 gap-2">
                        <h1 class="text-2xl font-black tracking-tight leading-tight">{item.name}</h1>
                        <div class="flex flex-wrap gap-1.5">
                            <span class="badge badge-ghost badge-xs font-bold opacity-50 uppercase tracking-wider">{item.category}</span>
                            <span class="badge badge-outline badge-xs font-black uppercase tracking-wider"
                                  style="color:{gradeColor(item.grade)};border-color:{gradeColor(item.grade)}55">{item.grade}</span>
                        </div>
                        <p class="text-[10px] font-mono opacity-30 uppercase tracking-widest">updated {timeAgo(item.updated_at)}</p>
                    </div>
                </div>

                {#if hasRecipe && craftTree}
                    <div class="card border border-warning/30 shadow-sm" style="background:color-mix(in oklch, var(--color-warning) 12%, transparent)">
                        <div class="card-body p-4 gap-1">
                            <p class="text-[10px] font-mono uppercase tracking-widest opacity-60">Profit / craft</p>
                            {#if profit != null}
                                <div class="text-4xl font-black tabular-nums" style="color:var(--color-warning)">
                                    {profit >= 0 ? '+' : ''}{formatCurrency(profit)}
                                </div>
                                <p class="text-xs font-mono opacity-60">
                                    {#if margin != null}margin {margin}% · {/if}
                                    sell {formatCurrency(item.current_price)} · cost {formatCurrency(materialCost)}
                                </p>
                                {#if margin != null}
                                    <div class="w-full bg-base-200 rounded-full h-1.5 mt-1 overflow-hidden">
                                        <div class="h-full rounded-full" style="width:{Math.min(100,Math.max(0,margin))}%;background:var(--color-warning)"></div>
                                    </div>
                                {/if}
                            {:else}
                                <div class="text-2xl font-black opacity-30">—</div>
                                <p class="text-xs font-mono opacity-40">missing prices</p>
                            {/if}
                        </div>
                    </div>
                {/if}

                <div class="card bg-base-100 border border-base-200 shadow-sm">
                    <div class="card-body p-4 gap-1">
                        <p class="text-[10px] font-mono uppercase tracking-widest opacity-40">Market price</p>
                        {#if item.current_price != null}
                            {@const p = splitCurrency(item.current_price)}
                            {#if p}
                            <div class="text-2xl font-black tabular-nums tracking-tight">
                                {#if p.gold > 0}<span>{p.gold}<span class="text-yellow-500 text-sm ml-0.5">g</span> </span>{/if}
                                {#if p.silver > 0 || p.gold > 0}<span>{p.silver.toString().padStart(2,'00')}<span class="text-slate-400 text-sm ml-0.5">s</span> </span>{/if}
                                <span>{p.bronze.toString().padStart(2,'0')}<span class="text-orange-700 text-sm ml-0.5">b</span></span>
                            </div>
                            {/if}
                        {:else}
                            <div class="text-xl font-black opacity-20 italic">No price data</div>
                        {/if}
                        {#if stats}
                            {@const statRows = /** @type {[string, number][]} */ ([['min', stats.min], ['max', stats.max], ['avg', stats.avg], ['last', stats.last]])}
                            <div class="grid grid-cols-4 gap-2 mt-2 pt-2 border-t border-base-200">
                                {#each statRows as [label, val]}
                                    <div>
                                        <p class="text-[9px] font-mono uppercase tracking-widest opacity-30">{label}</p>
                                        <p class="text-xs font-black tabular-nums truncate">{formatCurrency(val)}</p>
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- RIGHT: price history chart -->
            <div class="card bg-base-100 border border-base-200 shadow-sm overflow-hidden">
                <div class="flex items-center justify-between px-4 py-3 border-b border-base-200 bg-base-200/20">
                    <div class="flex items-center gap-2">
                        <h2 class="font-black text-xs uppercase tracking-widest opacity-60">Price history</h2>
                        {#if profitPill}
                            <span class="badge badge-xs font-mono {profitPill === 'above' ? 'badge-success' : 'badge-error'}">
                                {profitPill === 'above' ? '▲ above mat. cost' : '▼ below mat. cost'}
                            </span>
                        {/if}
                    </div>
                    <span class="text-[10px] font-mono opacity-30 uppercase">source: {SOURCE}</span>
                </div>
                <div class="p-4 min-h-[320px]">
                    {#if loadingHistory}
                        <div class="flex justify-center py-16"><span class="loading loading-spinner loading-lg text-primary"></span></div>
                    {:else if chartPoints.length === 0}
                        <div class="flex flex-col items-center justify-center py-16 opacity-30 gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"/></svg>
                            <span class="text-[10px] font-mono uppercase tracking-widest">No data for this range</span>
                        </div>
                    {:else}
                        <EChartsLineChart points={chartPoints} height={320} materialCost={materialCost} />
                    {/if}
                </div>
            </div>
        </div>

        <!-- Bottom: recipe full width -->
        {#if hasRecipe === false}
            <div class="card bg-base-100 border border-base-200 shadow-sm">
                <div class="card-body p-4 opacity-40 text-sm font-mono">No crafting recipe for this item.</div>
            </div>
        {:else if craftTree}
            <RecipeCard
                {craftTree}
                {batchSize}
                {nodeOverrides}
                {inventory}
                materialCost={materialCost ?? 0}
                {profit}
                onBatchChange={handleBatchChange}
                onToggleMode={handleToggleMode}
                onToggleExpand={handleToggleExpand}
                onInventoryUpdate={handleInventoryUpdate}
                onSetInventory={handleSetInventory}
            />
        {/if}
    </div>
```

- [ ] **Step 5: Verify svelte-check passes**

```bash
cd /home/dv6/GitHub/improved-octo-potato/frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors` (will warn about unknown prop `onSetInventory` on RecipeCard until Task 3 — that's OK, it's a JS codebase)

- [ ] **Step 6: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add frontend/src/routes/items/[id]/+page.svelte
git commit -m "feat(frontend): remove Follow button, recipe full-width at bottom"
```

---

## Task 2: Inline "Have" column in RecipeTree

**Files:**
- Modify: `frontend/src/lib/components/crafting/RecipeTree.svelte`

**What changes:**
- Add `onSetInventory: (id: number, value: number) => void` to props
- Add "Have" column header between "Need" and "Still need"
- Add `<input>` in every row between the Need cell and Still need cell
- Input calls `onSetInventory(node.item_id, parsedValue)` on change

- [ ] **Step 1: Add `onSetInventory` to props**

Replace the props line (line 11):

```js
    /** @type {{ nodes: IngredientNode[], batchSize: number, nodeOverrides: Record<number,{mode:'craft'|'buy',expanded:boolean}>, inventory: Record<number,number>, onToggleMode: (id:number)=>void, onToggleExpand: (id:number)=>void, onSetInventory: (id:number, value:number)=>void }} */
    let { nodes, batchSize, nodeOverrides, inventory, onToggleMode, onToggleExpand, onSetInventory } = $props();
```

- [ ] **Step 2: Add "Have" column header**

Replace the `<thead>` block:

```svelte
    <thead>
        <tr class="border-b-2 border-base-200 bg-base-200/40">
            <th class="w-1 p-0"></th>
            <th class="text-left py-2 pl-4 text-xs font-mono uppercase tracking-wider opacity-60">Ingredient</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Need</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Have</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Still need</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Unit</th>
            <th class="py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Mode</th>
            <th class="text-right py-2 pr-3 text-xs font-mono uppercase tracking-wider opacity-60">Subtotal</th>
        </tr>
    </thead>
```

- [ ] **Step 3: Add "Have" input cell in the snippet row**

Inside the `{#snippet treeRow(...)}`, after the `<!-- Need -->` cell and before `<!-- Still need -->`, add:

```svelte
        <!-- Have (inline inventory input) -->
        <td class="py-1 pr-2">
            <input
                type="number"
                min="0"
                value={have || ''}
                oninput={(e) => {
                    const v = parseInt(/** @type {HTMLInputElement} */(e.target).value);
                    onSetInventory(node.item_id, isNaN(v) ? 0 : v);
                }}
                class="input input-xs input-bordered w-20 text-right font-mono tabular-nums"
                placeholder="0"
            />
        </td>
```

- [ ] **Step 4: Verify svelte-check**

```bash
cd /home/dv6/GitHub/improved-octo-potato/frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 5: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add frontend/src/lib/components/crafting/RecipeTree.svelte
git commit -m "feat(crafting): inline Have column in recipe tree — replaces inventory modal"
```

---

## Task 3: Update RecipeCard — remove modal, add totalLabour, wire onSetInventory

**Files:**
- Modify: `frontend/src/lib/components/crafting/RecipeCard.svelte`

**What changes:**
- Add `onSetInventory` to props
- Remove `inventoryOpen` state, `InventoryModal` import, modal trigger button, `<InventoryModal>` component
- Add `handleSetInventory(itemId, value)` — merges into inventory and calls `onInventoryUpdate`
- Add `totalLabour` derived — sums all Labour-named nodes in active (non-buy) branches
- Add Labour row in footer
- Pass `onSetInventory` to `<RecipeTree>`

- [ ] **Step 1: Rewrite the full RecipeCard.svelte**

Replace the entire file content:

```svelte
<script>
    import { formatCurrency } from '$lib/currency.js';
    import RecipeTree from './RecipeTree.svelte';

    /**
     * @typedef {{ item_id: number, item_name: string, qty_needed: number,
     *   unit_price: number|null, total_cost: number, can_craft: boolean,
     *   crafts_possible: number|null, ingredients: any[] }} IngredientNode
     * @typedef {{ item_id: number, item_name: string, output_qty: number, multiplier: number,
     *   market_price: number|null, profit_per_craft: number|null, total_material_cost: number,
     *   has_missing_prices: boolean, ingredients: IngredientNode[] }} CraftResult
     */

    /** @type {{ craftTree: CraftResult, batchSize: number, nodeOverrides: Record<number,{mode:'craft'|'buy',expanded:boolean}>, inventory: Record<number,number>, materialCost: number, profit: number|null, onBatchChange: (n:number)=>void, onToggleMode: (id:number)=>void, onToggleExpand: (id:number)=>void, onInventoryUpdate: (inv:Record<number,number>)=>void, onSetInventory: (id:number, value:number)=>void }} */
    let { craftTree, batchSize, nodeOverrides, inventory, materialCost, profit, onBatchChange, onToggleMode, onToggleExpand, onInventoryUpdate, onSetInventory } = $props();

    const margin = $derived(
        profit != null && craftTree.market_price != null && craftTree.market_price > 0
            ? Math.round((profit / (craftTree.market_price * craftTree.output_qty * batchSize)) * 100)
            : null
    );

    const warnings = $derived(() => {
        /** @type {string[]} */
        const w = [];
        if (craftTree.has_missing_prices) w.push('Some ingredients have no market price — cost may be incomplete');
        return w;
    });

    /** @param {IngredientNode[]} nodes @returns {number} */
    function sumLabour(nodes) {
        let total = 0;
        for (const node of nodes) {
            if (node.item_name.toLowerCase() === 'labour') {
                total += node.qty_needed * batchSize;
            } else if (node.can_craft && nodeOverrides[node.item_id]?.mode !== 'buy' && node.ingredients.length > 0) {
                total += sumLabour(node.ingredients);
            }
        }
        return total;
    }

    const totalLabour = $derived(sumLabour(craftTree.ingredients));
</script>

<div class="card bg-base-100 border border-base-200 shadow-sm">
    <!-- Card header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-200">
        <h2 class="font-black text-xs uppercase tracking-widest opacity-60">Recipe</h2>
        <!-- Batch size stepper -->
        <div class="flex items-center gap-1">
            <button
                class="btn btn-xs btn-ghost border border-base-200"
                onclick={() => onBatchChange(Math.max(1, batchSize - 1))}
                disabled={batchSize <= 1}
            >−</button>
            <input
                type="number"
                min="1"
                max="999"
                value={batchSize}
                oninput={(e) => {
                    const v = parseInt(/** @type {HTMLInputElement} */(e.target).value);
                    if (v >= 1 && v <= 999) onBatchChange(v);
                }}
                class="input input-xs input-bordered w-14 text-center font-mono tabular-nums"
            />
            <button
                class="btn btn-xs btn-ghost border border-base-200"
                onclick={() => onBatchChange(Math.min(999, batchSize + 1))}
                disabled={batchSize >= 999}
            >+</button>
        </div>
    </div>

    <!-- Tree -->
    <div class="overflow-x-auto">
        <RecipeTree
            nodes={craftTree.ingredients}
            {batchSize}
            {nodeOverrides}
            {inventory}
            {onToggleMode}
            {onToggleExpand}
            {onSetInventory}
        />
    </div>

    <!-- Inline warnings -->
    {#each warnings() as warn}
        <div class="px-4 py-1 text-[11px] font-mono opacity-50">· {warn}</div>
    {/each}

    <!-- Footer -->
    <div class="border-t-2 border-base-200 bg-base-200/30 px-4 py-3 flex items-end justify-between gap-4 flex-wrap">
        <div class="flex gap-6 flex-wrap">
            <div>
                <div class="text-[10px] font-mono uppercase tracking-widest opacity-50 mb-0.5">Total material cost</div>
                <div class="text-2xl font-black tabular-nums font-mono">{formatCurrency(materialCost)}</div>
            </div>
            <div>
                <div class="text-[10px] font-mono uppercase tracking-widest opacity-50 mb-0.5">Total labour</div>
                <div class="text-2xl font-black tabular-nums font-mono">{totalLabour.toLocaleString()}</div>
            </div>
        </div>
        {#if profit != null}
            <div class="text-right">
                <div class="text-[10px] font-mono uppercase tracking-widest opacity-50 mb-0.5">Profit</div>
                <div class="text-xl font-black tabular-nums {profit >= 0 ? 'text-success' : 'text-error'}">
                    {profit >= 0 ? '+' : ''}{formatCurrency(profit)}
                    {#if margin != null}<span class="text-sm opacity-70 ml-1">{margin}%</span>{/if}
                </div>
            </div>
        {/if}
    </div>
</div>
```

- [ ] **Step 2: Verify svelte-check**

```bash
cd /home/dv6/GitHub/improved-octo-potato/frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 3: Run backend tests to confirm nothing broke**

```bash
cd /home/dv6/GitHub/improved-octo-potato && make test 2>&1 | tail -5
```
Expected: `67 passed`

- [ ] **Step 4: Commit**

```bash
cd /home/dv6/GitHub/improved-octo-potato
git add frontend/src/lib/components/crafting/RecipeCard.svelte
git commit -m "feat(crafting): remove inventory modal, inline Have column, Total Labour in footer"
```

---

## Task 4: Push and smoke test

- [ ] **Step 1: Push**

```bash
git push origin main
```

- [ ] **Step 2: Manual smoke test**

```
1. Open http://localhost:5173/items
2. Click "Blazing Sunridge Ingot"
3. Verify: top row = info cards (left) + chart (right)
4. Verify: recipe table is full width below
5. Verify: no Follow button anywhere
6. Verify: recipe table has 8 columns — depth bar | Ingredient | Need | Have | Still need | Unit | Mode | Subtotal
7. Enter a number in "Have" for Iron Ore → "Still need" updates immediately
8. Change batch size → "Need", "Still need", "Total Labour" in footer all update
9. Toggle a "craft" pill to "buy" → its Labour sub-nodes disappear from Total Labour
10. Verify "Total Labour" in footer shows non-zero for Blazing Sunridge Ingot
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| Remove Follow button | Task 1 |
| Recipe full width at bottom | Task 1 |
| Top: info left + chart right | Task 1 |
| Inline "Have" column in table | Task 2 |
| Input calls onSetInventory per row | Task 2 |
| Remove inventory modal | Task 3 |
| Total Labour in footer | Task 3 |
| Labour reacts to batch size | Task 3 — `sumLabour` uses `batchSize` |
| Labour respects buy/craft toggles | Task 3 — `sumLabour` skips buy branches |

**No TBD or placeholders.**

**Type consistency:** `onSetInventory: (id: number, value: number) => void` defined in Task 1 (`handleSetInventory`), accepted in Task 2 (RecipeTree prop), forwarded in Task 3 (RecipeCard → RecipeTree). Consistent throughout.

**Note:** `InventoryModal.svelte` file is left in place (not deleted) — it's imported nowhere after Task 3 so it's dead code but harmless. Can be cleaned up separately.
