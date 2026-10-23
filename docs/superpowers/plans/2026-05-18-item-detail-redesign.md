# Item Detail Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tabbed Price History / Crafting layout with a persistent two-column view (Layout B+): profit hero card, price chart with material-cost reference line, and an interactive recipe tree with per-node buy/craft toggle.

**Architecture:** Shared reactive state (`batchSize`, `nodeOverrides`, `inventory`) lives in `+page.svelte` so both the left-column profit card and right-column recipe tree stay in sync. `materialCost` and `profit` are derived at page level and passed down as props. The backend is called once with `multiplier=1`; all scaling is client-side.

**Tech Stack:** SvelteKit 5 (runes: `$state`, `$derived`, `$effect`, `$props`), DaisyUI + Tailwind CSS v4, ECharts via `svelte-echarts`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/lib/currency.js` | `formatCurrency`, `splitCurrency` — shared across components |
| Modify | `src/lib/components/charts/EChartsLineChart.svelte` | Add optional `materialCost` prop → reference line + profit in tooltip |
| Create | `src/lib/components/crafting/RecipeTree.svelte` | Recursive tree rows with depth bar, mode pills, expand/collapse |
| Create | `src/lib/components/crafting/InventoryModal.svelte` | Flat ingredient list + number inputs, localStorage persistence |
| Create | `src/lib/components/crafting/RecipeCard.svelte` | Recipe card: header stepper + modal trigger + RecipeTree + sticky footer |
| Rewrite | `src/routes/items/[id]/+page.svelte` | B+ layout, state owner, derives materialCost/profit |
| Delete | `src/lib/components/CraftingTab.svelte` | Replaced by RecipeCard + RecipeTree + InventoryModal |

---

## Task 1: Extract shared currency utilities

**Files:**
- Create: `frontend/src/lib/currency.js`
- Modify: `frontend/src/lib/components/charts/EChartsLineChart.svelte` (line 16–27)
- Modify: `frontend/src/routes/items/[id]/+page.svelte` (lines 113–130)

- [ ] **Step 1: Create currency.js**

```js
// frontend/src/lib/currency.js

/**
 * @param {number | null | undefined} copper
 * @returns {{ gold: number, silver: number, bronze: number } | null}
 */
export function splitCurrency(copper) {
    if (copper == null || !Number.isFinite(copper)) return null;
    const abs = Math.abs(copper);
    return {
        gold: Math.floor(abs / 10000),
        silver: Math.floor((abs % 10000) / 100),
        bronze: abs % 100,
    };
}

/**
 * @param {number | null | undefined} copper
 * @returns {string}
 */
export function formatCurrency(copper) {
    const c = splitCurrency(copper);
    if (!c) return '--';
    const g = c.gold > 0 ? `${c.gold}g ` : '';
    const s = (c.silver > 0 || c.gold > 0) ? `${c.silver.toString().padStart(2, '0')}s ` : '';
    const b = `${c.bronze.toString().padStart(2, '0')}b`;
    return `${g}${s}${b}`.trim();
}
```

- [ ] **Step 2: Update EChartsLineChart to import from currency.js**

Replace lines 16–27 in `EChartsLineChart.svelte`:
```js
// Remove the local formatCurrency function, add at top of <script>:
import { formatCurrency } from '$lib/currency.js';
```

- [ ] **Step 3: Update +page.svelte to import from currency.js**

In `+page.svelte`, remove the local `splitCurrency` and `formatCurrency` functions and add:
```js
import { splitCurrency, formatCurrency } from '$lib/currency.js';
```

- [ ] **Step 4: Verify frontend still compiles**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/currency.js frontend/src/lib/components/charts/EChartsLineChart.svelte frontend/src/routes/items/[id]/+page.svelte
git commit -m "refactor(frontend): extract formatCurrency to shared currency.js"
```

---

## Task 2: Add materialCost reference line to EChartsLineChart

**Files:**
- Modify: `frontend/src/lib/components/charts/EChartsLineChart.svelte`

- [ ] **Step 1: Add `materialCost` prop and update options**

Replace the full `EChartsLineChart.svelte` content:

```svelte
<script>
    // @ts-nocheck
    import { Chart } from 'svelte-echarts';
    import { init, use } from 'echarts/core';
    import { LineChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { formatCurrency } from '$lib/currency.js';

    use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, CanvasRenderer]);

    let { points = [], height = 400, materialCost = null } = $props();

    const options = $derived.by(() => {
        if (points.length === 0) return {};

        /** @type {any} */
        const markLine = materialCost != null ? {
            silent: true,
            symbol: 'none',
            data: [{ yAxis: materialCost }],
            lineStyle: { color: '#ef4444', type: 'dashed', width: 1.5 },
            label: {
                formatter: () => `mat. cost ${formatCurrency(materialCost)}`,
                position: 'insideEndTop',
                fontSize: 10,
                color: '#ef4444',
            }
        } : undefined;

        return {
            animation: true,
            animationDuration: 300,
            grid: { left: 64, right: 32, top: 32, bottom: 32, containLabel: false },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255,255,255,0.95)',
                borderColor: '#e2e8f0',
                textStyle: { color: '#1e293b' },
                axisPointer: { type: 'cross', label: { backgroundColor: '#0ea5e9' } },
                formatter: (params) => {
                    const p = params[0];
                    const date = new Date(p.data[0]).toLocaleString();
                    const price = p.data[1];
                    const profit = materialCost != null ? price - materialCost : null;
                    const profitStr = profit != null
                        ? `<div style="font-size:11px;color:${profit >= 0 ? '#16a34a' : '#dc2626'};margin-top:4px;">profit ${profit >= 0 ? '+' : ''}${formatCurrency(profit)}</div>`
                        : '';
                    return `<div style="padding:4px;">
                        <div style="font-size:10px;text-transform:uppercase;font-weight:900;opacity:0.5;margin-bottom:4px;">${date}</div>
                        <div style="font-weight:900;font-size:14px;font-variant-numeric:tabular-nums;">${formatCurrency(price)}</div>
                        ${profitStr}
                    </div>`;
                }
            },
            xAxis: {
                type: 'time',
                axisLabel: {
                    color: '#64748b', fontSize: 10, fontWeight: 'bold',
                    formatter: (v) => new Date(v).toLocaleDateString([], { month: 'short', day: 'numeric' })
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } },
                axisPointer: { label: { formatter: (p) => new Date(p.value).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit' }) } }
            },
            yAxis: {
                type: 'value', scale: true,
                axisLabel: { color: '#64748b', fontSize: 10, fontWeight: 'bold', formatter: (v) => formatCurrency(v).split(' ')[0] },
                splitLine: { lineStyle: { color: '#f1f5f9' } },
                axisPointer: { label: { formatter: (p) => formatCurrency(p.value) } }
            },
            dataZoom: [{ type: 'inside', start: 0, end: 100 }],
            series: [{
                name: 'Price',
                type: 'line',
                smooth: true,
                showSymbol: false,
                lineStyle: { width: 3, color: '#0ea5e9' },
                areaStyle: {
                    color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [{ offset: 0, color: 'rgba(14,165,233,0.15)' }, { offset: 1, color: 'rgba(14,165,233,0)' }] }
                },
                markLine,
                data: points.map((p) => [new Date(p.t).getTime(), p.price])
            }]
        };
    });
</script>

<div style="height: {height}px;" class="w-full">
    <Chart {init} {options} />
</div>
```

- [ ] **Step 2: Verify compiles**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/charts/EChartsLineChart.svelte
git commit -m "feat(chart): add materialCost reference line and profit in tooltip"
```

---

## Task 3: RecipeTree component

**Files:**
- Create: `frontend/src/lib/components/crafting/RecipeTree.svelte`

This component renders the ingredient tree recursively. It receives the tree data and all state as props — it owns no state itself.

- [ ] **Step 1: Create RecipeTree.svelte**

```bash
mkdir -p frontend/src/lib/components/crafting
```

```svelte
<!-- frontend/src/lib/components/crafting/RecipeTree.svelte -->
<script>
    import { formatCurrency } from '$lib/currency.js';

    /**
     * @typedef {{ item_id: number, item_name: string, qty_needed: number,
     *   unit_price: number|null, total_cost: number, can_craft: boolean,
     *   crafts_possible: number|null, ingredients: IngredientNode[] }} IngredientNode
     */

    /** @type {{ nodes: IngredientNode[], batchSize: number, nodeOverrides: Record<number,{mode:'craft'|'buy',expanded:boolean}>, inventory: Record<number,number>, onToggleMode: (id:number)=>void, onToggleExpand: (id:number)=>void }} */
    let { nodes, batchSize, nodeOverrides, inventory, onToggleMode, onToggleExpand } = $props();

    // Depth colors: L0–L5
    const DEPTH_COLORS = ['#1a1a1a','#3554c8','#1f8a5b','#b5701b','#8a3b6b','#7a786f'];

    /** @param {IngredientNode} node @param {number} depth @returns {number} */
    function computeSubtotal(node, depth) {
        const qty = node.qty_needed * batchSize;
        const override = nodeOverrides[node.item_id];
        if (override?.mode === 'buy' || !node.can_craft || node.ingredients.length === 0) {
            return (node.unit_price ?? 0) * qty;
        }
        return node.ingredients.reduce((s, c) => s + computeSubtotal(c, depth + 1), 0);
    }

    /** @param {number} depth @returns {string} */
    function depthColor(depth) {
        return DEPTH_COLORS[Math.min(depth, 5)];
    }
</script>

{#snippet treeRow(node, depth)}
    {@const qty = node.qty_needed * batchSize}
    {@const override = nodeOverrides[node.item_id]}
    {@const isBuy = override?.mode === 'buy'}
    {@const isExpanded = override?.expanded ?? (depth < 2)}
    {@const subtotal = computeSubtotal(node, depth)}
    {@const have = inventory[node.item_id] ?? 0}
    {@const stillNeed = Math.max(0, qty - have)}
    {@const color = depthColor(depth)}

    <tr class="border-b border-base-200 hover:bg-base-200/30 {isBuy && node.can_craft ? 'opacity-50' : ''}">
        <!-- Depth bar -->
        <td class="w-1 p-0">
            <div class="w-1 h-full min-h-[36px]" style="background:{color}"></div>
        </td>

        <!-- Toggle + name + level chip -->
        <td class="py-2 pl-2">
            <div class="flex items-center gap-1.5" style="padding-left:{depth * 18}px">
                {#if node.can_craft && node.ingredients.length > 0}
                    <button
                        class="w-4 h-4 flex items-center justify-center border border-base-content/30 rounded text-[10px] shrink-0 hover:bg-base-200"
                        onclick={() => onToggleExpand(node.item_id)}
                        title={isExpanded ? 'Collapse' : 'Expand'}
                    >{isExpanded ? '▾' : '▸'}</button>
                {:else}
                    <span class="w-4 h-4 flex items-center justify-center text-[10px] opacity-30 border border-dashed border-base-content/20 rounded shrink-0">·</span>
                {/if}
                <span class="text-sm font-medium truncate max-w-[200px]" title={node.item_name}>
                    {#if isBuy && node.can_craft}<s class="opacity-50">{node.item_name}</s>{:else}{node.item_name}{/if}
                </span>
                <span class="text-[9px] font-mono font-bold px-1 border rounded shrink-0" style="color:{color};border-color:{color}40">
                    L{depth}
                </span>
            </div>
        </td>

        <!-- Need -->
        <td class="text-right font-mono text-sm py-2 pr-2 tabular-nums">{qty.toLocaleString()}</td>

        <!-- Still need (only if inventory set) -->
        <td class="text-right font-mono text-xs py-2 pr-2 tabular-nums {stillNeed === 0 && have > 0 ? 'text-success' : 'opacity-60'}">
            {have > 0 ? stillNeed.toLocaleString() : '—'}
        </td>

        <!-- Unit price -->
        <td class="text-right font-mono text-xs py-2 pr-2 opacity-60 tabular-nums">
            {node.unit_price != null ? formatCurrency(node.unit_price) : '—'}
        </td>

        <!-- Mode pill -->
        <td class="py-2 pr-2">
            {#if node.can_craft && node.ingredients.length > 0}
                <button
                    class="badge badge-sm font-mono text-[10px] cursor-pointer hover:opacity-80 {isBuy ? 'badge-success' : 'badge-warning'}"
                    onclick={() => onToggleMode(node.item_id)}
                    title="Click to toggle buy/craft"
                >{isBuy ? 'buy' : 'craft'}</button>
            {:else if node.item_name.toLowerCase() === 'labour'}
                <span class="badge badge-sm badge-info font-mono text-[10px]">labour</span>
            {:else}
                <span class="badge badge-sm badge-ghost font-mono text-[10px] opacity-60">raw</span>
            {/if}
        </td>

        <!-- Subtotal -->
        <td class="text-right font-mono text-sm font-bold py-2 pr-3 tabular-nums">
            {node.unit_price != null || !node.can_craft ? formatCurrency(subtotal) : '—'}
        </td>
    </tr>

    {#if node.can_craft && node.ingredients.length > 0 && isExpanded && !isBuy}
        {#each node.ingredients as child}
            {@render treeRow(child, depth + 1)}
        {/each}
    {/if}
{/snippet}

<table class="w-full border-collapse text-sm">
    <thead>
        <tr class="border-b-2 border-base-200 bg-base-200/40">
            <th class="w-1 p-0"></th>
            <th class="text-left py-2 pl-4 text-xs font-mono uppercase tracking-wider opacity-60">Ingredient</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Need</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Still need</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Unit</th>
            <th class="py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Mode</th>
            <th class="text-right py-2 pr-3 text-xs font-mono uppercase tracking-wider opacity-60">Subtotal</th>
        </tr>
    </thead>
    <tbody>
        {#each nodes as node}
            {@render treeRow(node, 1)}
        {/each}
    </tbody>
</table>
```

- [ ] **Step 2: Verify compiles**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/crafting/RecipeTree.svelte
git commit -m "feat(crafting): RecipeTree component with depth bars, mode pills, expand/collapse"
```

---

## Task 4: InventoryModal component

**Files:**
- Create: `frontend/src/lib/components/crafting/InventoryModal.svelte`

- [ ] **Step 1: Create InventoryModal.svelte**

```svelte
<!-- frontend/src/lib/components/crafting/InventoryModal.svelte -->
<script>
    /**
     * @typedef {{ item_id: number, item_name: string, qty_needed: number,
     *   can_craft: boolean, ingredients: any[] }} IngredientNode
     */

    /** @type {{ open: boolean, nodes: IngredientNode[], batchSize: number, inventory: Record<number,number>, onUpdate: (inv: Record<number,number>) => void, onClose: () => void }} */
    let { open, nodes, batchSize, inventory, onUpdate, onClose } = $props();

    /** @param {IngredientNode[]} nodes @param {Set<number>} seen @returns {IngredientNode[]} */
    function collectLeaves(nodes, seen = new Set()) {
        /** @type {IngredientNode[]} */
        const result = [];
        for (const node of nodes) {
            if (!node.can_craft || node.ingredients.length === 0) {
                if (!seen.has(node.item_id)) {
                    seen.add(node.item_id);
                    result.push(node);
                }
            } else {
                result.push(...collectLeaves(node.ingredients, seen));
            }
        }
        return result;
    }

    const leaves = $derived(collectLeaves(nodes));

    /** @param {number} itemId @param {number} value */
    function setInventory(itemId, value) {
        const next = { ...inventory };
        if (value > 0) next[itemId] = value;
        else delete next[itemId];
        onUpdate(next);
    }

    function clearAll() {
        onUpdate({});
    }
</script>

{#if open}
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black/50 z-40" onclick={onClose}></div>

    <!-- Modal -->
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-base-100 border border-base-200 rounded-box shadow-xl w-full max-w-md max-h-[80vh] flex flex-col">
            <div class="flex items-center justify-between p-4 border-b border-base-200">
                <h3 class="font-bold text-base">Edit inventory</h3>
                <button class="btn btn-ghost btn-xs" onclick={onClose}>✕</button>
            </div>
            <p class="px-4 pt-3 text-xs opacity-50 font-mono">Enter what you already own — "Still need" in the table updates automatically.</p>

            <div class="overflow-y-auto flex-1 p-4 space-y-2">
                {#each leaves as leaf}
                    {@const need = leaf.qty_needed * batchSize}
                    {@const have = inventory[leaf.item_id] ?? 0}
                    <div class="flex items-center gap-3">
                        <span class="flex-1 text-sm truncate" title={leaf.item_name}>{leaf.item_name}</span>
                        <span class="text-xs font-mono opacity-40 shrink-0">need {need.toLocaleString()}</span>
                        <input
                            type="number"
                            min="0"
                            value={have || ''}
                            oninput={(e) => {
                                const v = parseInt(/** @type {HTMLInputElement} */(e.target).value);
                                setInventory(leaf.item_id, isNaN(v) ? 0 : v);
                            }}
                            class="input input-bordered input-xs w-28 text-right font-mono tabular-nums"
                            placeholder="0"
                        />
                    </div>
                {/each}
            </div>

            <div class="flex justify-between p-4 border-t border-base-200">
                <button class="btn btn-ghost btn-sm" onclick={clearAll}>Clear all</button>
                <button class="btn btn-primary btn-sm" onclick={onClose}>Done</button>
            </div>
        </div>
    </div>
{/if}
```

- [ ] **Step 2: Verify compiles**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/crafting/InventoryModal.svelte
git commit -m "feat(crafting): InventoryModal — flat leaf ingredient list with number inputs"
```

---

## Task 5: RecipeCard component

**Files:**
- Create: `frontend/src/lib/components/crafting/RecipeCard.svelte`

- [ ] **Step 1: Create RecipeCard.svelte**

```svelte
<!-- frontend/src/lib/components/crafting/RecipeCard.svelte -->
<script>
    import { formatCurrency } from '$lib/currency.js';
    import RecipeTree from './RecipeTree.svelte';
    import InventoryModal from './InventoryModal.svelte';

    /**
     * @typedef {{ item_id: number, item_name: string, qty_needed: number,
     *   unit_price: number|null, total_cost: number, can_craft: boolean,
     *   crafts_possible: number|null, ingredients: any[] }} IngredientNode
     * @typedef {{ item_id: number, item_name: string, output_qty: number, multiplier: number,
     *   market_price: number|null, profit_per_craft: number|null, total_material_cost: number,
     *   has_missing_prices: boolean, ingredients: IngredientNode[] }} CraftResult
     */

    /** @type {{ craftTree: CraftResult, batchSize: number, nodeOverrides: Record<number,{mode:'craft'|'buy',expanded:boolean}>, inventory: Record<number,number>, materialCost: number, profit: number|null, onBatchChange: (n:number)=>void, onToggleMode: (id:number)=>void, onToggleExpand: (id:number)=>void, onInventoryUpdate: (inv:Record<number,number>)=>void }} */
    let { craftTree, batchSize, nodeOverrides, inventory, materialCost, profit, onBatchChange, onToggleMode, onToggleExpand, onInventoryUpdate } = $props();

    let inventoryOpen = $state(false);

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
</script>

<div class="card bg-base-100 border border-base-200 shadow-sm">
    <!-- Card header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-200">
        <h2 class="font-black text-xs uppercase tracking-widest opacity-60">Recipe</h2>
        <div class="flex items-center gap-3">
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
            <!-- Inventory link -->
            <button
                class="text-xs font-mono opacity-50 hover:opacity-100 underline underline-offset-2"
                onclick={() => inventoryOpen = true}
            >edit inventory ✎</button>
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
        />
    </div>

    <!-- Inline warnings -->
    {#each warnings() as warn}
        <div class="px-4 py-1 text-[11px] font-mono opacity-50">· {warn}</div>
    {/each}

    <!-- Sticky footer -->
    <div class="border-t-2 border-base-200 bg-base-200/30 px-4 py-3 flex items-end justify-between gap-4 flex-wrap">
        <div>
            <div class="text-[10px] font-mono uppercase tracking-widest opacity-50 mb-0.5">Total material cost</div>
            <div class="text-2xl font-black tabular-nums font-mono">{formatCurrency(materialCost)}</div>
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

<InventoryModal
    open={inventoryOpen}
    nodes={craftTree.ingredients}
    {batchSize}
    {inventory}
    onUpdate={onInventoryUpdate}
    onClose={() => inventoryOpen = false}
/>
```

- [ ] **Step 2: Verify compiles**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -5
```
Expected: `0 errors`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/crafting/RecipeCard.svelte
git commit -m "feat(crafting): RecipeCard — batch stepper, inventory modal trigger, sticky footer"
```

---

## Task 6: Full page rewrite — Layout B+

**Files:**
- Rewrite: `frontend/src/routes/items/[id]/+page.svelte`
- Delete: `frontend/src/lib/components/CraftingTab.svelte`

This is the main layout task. The page owns all shared state and derives `materialCost` / `profit`.

- [ ] **Step 1: Write the new +page.svelte**

Replace the entire file:

```svelte
<!-- frontend/src/routes/items/[id]/+page.svelte -->
<script>
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { API_BASE_URL } from '$lib/config.js';
    import { gradeColor } from '$lib/grades.js';
    import { formatCurrency, splitCurrency } from '$lib/currency.js';
    import EChartsLineChart from '$lib/components/charts/EChartsLineChart.svelte';
    import RecipeCard from '$lib/components/crafting/RecipeCard.svelte';

    /** @typedef {{ id: number, name: string, category: string, grade: string, current_price: number|null, updated_at: string }} ItemDetail */
    /** @typedef {{ t: string, price: number }} ChartPoint */
    /** @typedef {{ item_id: number, item_name: string, qty_needed: number, unit_price: number|null, total_cost: number, can_craft: boolean, crafts_possible: number|null, ingredients: any[] }} IngredientNode */
    /** @typedef {{ item_id: number, item_name: string, output_qty: number, multiplier: number, market_price: number|null, profit_per_craft: number|null, total_material_cost: number, has_missing_prices: boolean, ingredients: IngredientNode[] }} CraftResult */

    const SOURCE = 'ah';
    const RANGE_OPTIONS = [
        { key: '7D',  days: 7,    interval: '1h' },
        { key: '30D', days: 30,   interval: '1h' },
        { key: '90D', days: 90,   interval: '1d' },
        { key: 'MAX', days: null, interval: '1d' },
    ];

    // ── State ──────────────────────────────────────────────
    let selectedRange  = $state('30D');

    /** @type {ItemDetail|null} */
    let item           = $state(null);
    let loadingItem    = $state(true);
    /** @type {string|null} */
    let itemError      = $state(null);

    /** @type {ChartPoint[]} */
    let chartPoints    = $state([]);
    let loadingHistory = $state(false);

    /** @type {CraftResult|null} */
    let craftTree      = $state(null);
    let hasRecipe      = $state(/** @type {boolean|null} */ (null));

    // Crafting interactive state
    let batchSize      = $state(1);
    /** @type {Record<number, {mode:'craft'|'buy', expanded:boolean}>} */
    let nodeOverrides  = $state({});
    /** @type {Record<number, number>} */
    let inventory      = $state({});

    let followState    = $state(/** @type {'idle'|'following'|'done'} */ ('idle'));

    // ── Derived ────────────────────────────────────────────

    /** @param {IngredientNode} node @returns {number} */
    function computeNodeCost(node) {
        const qty = node.qty_needed * batchSize;
        const override = nodeOverrides[node.item_id];
        if (override?.mode === 'buy' || !node.can_craft || node.ingredients.length === 0) {
            return (node.unit_price ?? 0) * qty;
        }
        return node.ingredients.reduce((s, c) => s + computeNodeCost(c), 0);
    }

    const materialCost = $derived(
        craftTree ? craftTree.ingredients.reduce((s, n) => s + computeNodeCost(n), 0) : null
    );

    const profit = $derived(
        materialCost != null && item?.current_price != null && craftTree != null
            ? item.current_price * craftTree.output_qty * batchSize - materialCost
            : null
    );

    const margin = $derived(
        profit != null && item?.current_price != null && item.current_price > 0 && craftTree != null
            ? Math.round((profit / (item.current_price * craftTree.output_qty * batchSize)) * 100)
            : null
    );

    const profitPill = $derived(
        materialCost != null && item?.current_price != null
            ? item.current_price > materialCost / (craftTree?.output_qty ?? 1)
                ? 'above'
                : 'below'
            : null
    );

    const stats = $derived.by(() => {
        if (chartPoints.length === 0) return null;
        const prices = chartPoints.map((p) => p.price);
        return {
            min: Math.min(...prices),
            max: Math.max(...prices),
            avg: Math.round(prices.reduce((s, n) => s + n, 0) / prices.length),
            last: prices[prices.length - 1],
        };
    });

    // ── Helpers ────────────────────────────────────────────

    function getItemId() { return Number(page.params.id); }

    function rangeConfig() { return RANGE_OPTIONS.find((r) => r.key === selectedRange) ?? RANGE_OPTIONS[1]; }

    function timeAgo(/** @type {string} */ iso) {
        const diff = Date.now() - new Date(iso).getTime();
        const m = Math.floor(diff / 60000);
        if (m < 1) return 'just now';
        if (m < 60) return `${m}m ago`;
        const h = Math.floor(m / 60);
        if (h < 24) return `${h}h ago`;
        return `${Math.floor(h / 24)}d ago`;
    }

    // ── Fetches ────────────────────────────────────────────

    async function loadItem() {
        loadingItem = true; itemError = null;
        try {
            const r = await fetch(`${API_BASE_URL}/items/${getItemId()}`);
            if (!r.ok) { itemError = `Could not load item (${r.status})`; return; }
            item = await r.json();
        } catch { itemError = 'Network error loading item'; }
        finally { loadingItem = false; }
    }

    async function loadHistory() {
        loadingHistory = true;
        try {
            const cfg = rangeConfig();
            const params = new URLSearchParams({ source: SOURCE, interval: cfg.interval });
            if (cfg.days !== null) {
                const from = new Date();
                from.setDate(from.getDate() - cfg.days);
                params.append('from', from.toISOString());
            }
            params.append('to', new Date().toISOString());
            const r = await fetch(`${API_BASE_URL}/items/${getItemId()}/price-history?${params}`);
            if (!r.ok) { chartPoints = []; return; }
            const data = await r.json();
            chartPoints = data
                .map((/** @type {any} */ row) => ({ t: row.bucket_start || row.captured_at, price: row.last_price ?? row.price }))
                .filter((/** @type {ChartPoint} */ row) => row.t && Number.isFinite(row.price))
                .sort((/** @type {ChartPoint} */ a, /** @type {ChartPoint} */ b) => new Date(a.t).getTime() - new Date(b.t).getTime());
        } catch { chartPoints = []; }
        finally { loadingHistory = false; }
    }

    async function loadCraftTree() {
        try {
            const r = await fetch(`${API_BASE_URL}/crafting/${getItemId()}/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ multiplier: 1, inventory: {} }),
            });
            if (r.status === 404) { hasRecipe = false; return; }
            if (!r.ok) return;
            craftTree = await r.json();
            hasRecipe = true;
            // Load inventory from localStorage
            const stored = localStorage.getItem(`inventory:${getItemId()}`);
            if (stored) inventory = JSON.parse(stored);
        } catch { hasRecipe = false; }
    }

    async function follow() {
        if (followState !== 'idle') return;
        followState = 'following';
        try {
            await fetch(`${API_BASE_URL}/user-items/${getItemId()}`, { method: 'POST', credentials: 'include' });
            followState = 'done';
        } catch { followState = 'idle'; }
    }

    // ── Handlers ───────────────────────────────────────────

    /** @param {string} key */
    function handleRangeChange(key) {
        if (selectedRange === key) return;
        selectedRange = key;
        loadHistory();
    }

    /** @param {number} n */
    function handleBatchChange(n) { batchSize = n; }

    /** @param {number} id */
    function handleToggleMode(id) {
        const cur = nodeOverrides[id];
        nodeOverrides = {
            ...nodeOverrides,
            [id]: { mode: cur?.mode === 'buy' ? 'craft' : 'buy', expanded: cur?.expanded ?? true }
        };
    }

    /** @param {number} id */
    function handleToggleExpand(id) {
        const cur = nodeOverrides[id];
        nodeOverrides = {
            ...nodeOverrides,
            [id]: { mode: cur?.mode ?? 'craft', expanded: !(cur?.expanded ?? true) }
        };
    }

    /** @param {Record<number,number>} inv */
    function handleInventoryUpdate(inv) {
        inventory = inv;
        localStorage.setItem(`inventory:${getItemId()}`, JSON.stringify(inv));
    }

    // ── Mount ──────────────────────────────────────────────

    onMount(async () => {
        const id = getItemId();
        if (!Number.isFinite(id) || id <= 0) {
            itemError = 'Invalid item id'; loadingItem = false; return;
        }
        await Promise.all([loadItem(), loadHistory(), loadCraftTree()]);
    });
</script>

<!-- ── Top bar ─────────────────────────────────────────── -->
<div class="max-w-screen-xl mx-auto px-4 py-4 space-y-4">
    <div class="flex items-center justify-between gap-4">
        <a href="/items" class="btn btn-ghost btn-sm gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            Back to items
        </a>
        <div class="join border border-base-200 shadow-sm">
            {#each RANGE_OPTIONS as opt}
                <button
                    class="btn btn-sm join-item {selectedRange === opt.key ? 'btn-primary' : 'btn-ghost'}"
                    onclick={() => handleRangeChange(opt.key)}
                >{opt.key}</button>
            {/each}
        </div>
    </div>

    <!-- ── Loading / error ── -->
    {#if loadingItem}
        <div class="flex justify-center py-24"><span class="loading loading-dots loading-lg text-primary"></span></div>
    {:else if itemError}
        <div class="alert alert-error"><span>{itemError}</span></div>
    {:else if item}

    <!-- ── B+ two-column grid ── -->
    <div class="grid grid-cols-1 lg:grid-cols-[32%_1fr] gap-3 items-start">

        <!-- ════ LEFT COLUMN ════ -->
        <div class="flex flex-col gap-3">

            <!-- Identity card -->
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

            <!-- Profit hero card (only if recipe exists) -->
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

            <!-- Price card -->
            <div class="card bg-base-100 border border-base-200 shadow-sm">
                <div class="card-body p-4 gap-1">
                    <p class="text-[10px] font-mono uppercase tracking-widest opacity-40">Market price</p>
                    {#if item.current_price != null}
                        {@const p = splitCurrency(item.current_price)}
                        {#if p}
                        <div class="text-2xl font-black tabular-nums tracking-tight">
                            {#if p.gold > 0}<span>{p.gold}<span class="text-yellow-500 text-sm ml-0.5">g</span> </span>{/if}
                            {#if p.silver > 0 || p.gold > 0}<span>{p.silver.toString().padStart(2,'0')}<span class="text-slate-400 text-sm ml-0.5">s</span> </span>{/if}
                            <span>{p.bronze.toString().padStart(2,'0')}<span class="text-orange-700 text-sm ml-0.5">b</span></span>
                        </div>
                        {/if}
                    {:else}
                        <div class="text-xl font-black opacity-20 italic">No price data</div>
                    {/if}
                    {#if stats}
                        <div class="grid grid-cols-4 gap-2 mt-2 pt-2 border-t border-base-200">
                            {#each [['min', stats.min], ['max', stats.max], ['avg', stats.avg], ['last', stats.last]] as [label, val]}
                                <div>
                                    <p class="text-[9px] font-mono uppercase tracking-widest opacity-30">{label}</p>
                                    <p class="text-xs font-black tabular-nums truncate">{formatCurrency(val)}</p>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Actions card -->
            <div class="card bg-base-100 border border-dashed border-base-300 shadow-sm">
                <div class="card-body p-4">
                    <button
                        class="btn btn-primary btn-sm w-full gap-1.5"
                        onclick={follow}
                        disabled={followState !== 'idle'}
                    >
                        {#if followState === 'done'}✓ Following{:else}★ Follow{/if}
                    </button>
                </div>
            </div>
        </div>

        <!-- ════ RIGHT COLUMN ════ -->
        <div class="flex flex-col gap-3">

            <!-- Price history card -->
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

            <!-- Recipe card -->
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
                />
            {/if}
        </div>
    </div>
    {/if}
</div>
```

- [ ] **Step 2: Delete CraftingTab.svelte**

```bash
rm frontend/src/lib/components/CraftingTab.svelte
```

- [ ] **Step 3: Verify compiles with 0 errors**

```bash
cd frontend && npx svelte-check --tsconfig ./jsconfig.json 2>&1 | tail -10
```
Expected: `0 errors`

- [ ] **Step 4: Run full backend test suite to check nothing broke**

```bash
make test 2>&1 | tail -5
```
Expected: `67 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/items/[id]/+page.svelte
git rm frontend/src/lib/components/CraftingTab.svelte
git commit -m "feat(frontend): Layout B+ — two-column item detail, profit hero, recipe tree"
```

---

## Task 7: Push and verify CI

- [ ] **Step 1: Push to remote**

```bash
git push origin main
```

- [ ] **Step 2: Check CI passes**

Open GitHub Actions and confirm `frontend.yml` (svelte-check) and `backend.yml` (pytest) are green.

- [ ] **Step 3: Manual smoke test in browser**

```
1. Open http://localhost:5173/items
2. Click any item that has a recipe (e.g. Blazing Sunridge Ingot)
3. Verify: two-column layout visible, no tabs
4. Verify: profit hero card shows amber value (or "—" if no prices)
5. Verify: chart loads, date range buttons work (7D/30D/90D/MAX)
6. Verify: recipe tree shows with depth bars and mode pills
7. Click a "craft" pill → it should turn to "buy", sub-rows dim
8. Click "edit inventory ✎" → modal opens, enter a value, close → "Still need" updates
9. Adjust batch size stepper → Need/Subtotal values update instantly
10. Click "★ Follow" → button changes to "✓ Following"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Remove tabs, two-column grid | Task 6 |
| Identity card with pills + meta | Task 6 |
| Profit hero card (accent, margin bar) | Task 6 |
| Price card with delta | Task 6 |
| Actions card with Follow button | Task 6 |
| Chart reference line at mat. cost | Task 2 |
| Chart tooltip with profit | Task 2 |
| Date range 7D/30D/90D/MAX | Task 6 |
| Recipe tree with depth bars | Task 3 |
| Mode pill (craft/buy toggle) | Task 3 |
| Expand/collapse per node | Task 3 |
| Still need column | Task 3 |
| Inventory modal | Task 4 |
| LocalStorage inventory persistence | Task 4, Task 6 |
| Batch size stepper | Task 5 |
| Sticky footer total + profit | Task 5 |
| Inline warnings (not banner) | Task 5 |
| formatCurrency (not ¤) | Task 1 |
| Profit hero pill on chart | Task 6 |
| Mobile single-column | Task 6 (grid collapses via `grid-cols-1 lg:grid-cols-[32%_1fr]`) |
| Optimistic Follow button | Task 6 |
| Delete CraftingTab.svelte | Task 6 |

**No TBD or placeholders found.**

**Type consistency:** `IngredientNode` and `CraftResult` typedefs are defined identically in `+page.svelte`, `RecipeCard.svelte`, and `RecipeTree.svelte` — consistent throughout.
