<script lang="ts">
    import { formatCurrency } from '$lib/currency.js';
    import RecipeTree from './RecipeTree.svelte';
    import { LABOUR_ITEM_NAME } from '$lib/crafting.js';
    import type { CraftResult, CraftNode, NodeOverride } from '$lib/types';

    let { craftTree, batchSize, nodeOverrides, inventory, materialCost, profit, onBatchChange, onToggleMode, onToggleExpand, onSetInventory }: {
        craftTree: CraftResult
        batchSize: number
        nodeOverrides: Record<number, NodeOverride>
        inventory: Record<number, number>
        materialCost: number
        profit: number | null
        onBatchChange: (n: number) => void
        onToggleMode: (id: number) => void
        onToggleExpand: (id: number) => void
        onSetInventory: (id: number, value: number) => void
    } = $props();

    const margin = $derived(
        profit != null && craftTree.market_price != null && craftTree.market_price > 0
            ? Math.round((profit / (craftTree.market_price * craftTree.output_qty * batchSize)) * 100)
            : null
    );

    const warnings = $derived.by(() => {
        const w: string[] = [];
        if (craftTree.has_missing_prices) w.push('Some ingredients have no market price — cost may be incomplete');
        return w;
    });

    /**
     * Sum labour across the active tree, respecting inventory and output_qty (same logic as computeNodeCost).
     */
    function sumLabour(nodes: CraftNode[], scale: number = batchSize): number {
        let total = 0;
        for (const node of nodes) {
            const qty = node.qty_needed * scale;
            const have = inventory[node.item_id] ?? 0;
            const stillNeed = Math.max(0, qty - have);
            if (stillNeed === 0) continue;

            if (node.item_name.toLowerCase() === LABOUR_ITEM_NAME) {
                total += stillNeed;
            } else if (node.can_craft && nodeOverrides[node.item_id]?.mode !== 'buy' && node.ingredients.length > 0) {
                const outputQty = node.output_qty ?? 1;
                const storedCrafts = Math.ceil(node.qty_needed / outputQty);
                const desiredCrafts = Math.ceil(stillNeed / outputQty);
                const childScale = storedCrafts > 0 ? desiredCrafts / storedCrafts : 0;
                total += sumLabour(node.ingredients, childScale);
            }
        }
        return total;
    }

    const totalLabour = $derived(sumLabour(craftTree.ingredients, batchSize));
</script>

<div class="card bg-base-100 border border-base-200 shadow-sm">
    <!-- Card header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-200">
        <h2 class="font-black text-xs uppercase tracking-widest opacity-60">Recipe</h2>
        <!-- Batch size stepper only -->
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
                    const v = parseInt((e.target as HTMLInputElement).value);
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
    {#each warnings as warn}
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
