<script lang="ts">
    import { formatCurrency } from '$lib/currency.js';
    import { LABOUR_ITEM_NAME } from '$lib/crafting.js';
    import type { CraftNode, NodeOverride } from '$lib/types';

    let { nodes, batchSize, nodeOverrides, inventory, onToggleMode, onToggleExpand, onSetInventory }: {
        nodes: CraftNode[]
        batchSize: number
        nodeOverrides: Record<number, NodeOverride>
        inventory: Record<number, number>
        onToggleMode: (id: number) => void
        onToggleExpand: (id: number) => void
        onSetInventory: (id: number, value: number) => void
    } = $props();

    // Depth colors: L0–L5
    const DEPTH_COLORS = ['#1a1a1a','#3554c8','#1f8a5b','#b5701b','#8a3b6b','#7a786f'];

    function computeNodeCost(node: CraftNode, scale: number): number {
        const qty = node.qty_needed * scale;
        const have = inventory[node.item_id] ?? 0;
        const stillNeed = Math.max(0, qty - have);
        const override = nodeOverrides[node.item_id];
        if (override?.mode === 'buy' || !node.can_craft || node.ingredients.length === 0) {
            return (node.unit_price ?? 0) * stillNeed;
        }
        if (stillNeed === 0) return 0;
        const outputQty = node.output_qty ?? 1;
        const storedCrafts = Math.ceil(node.qty_needed / outputQty);
        const desiredCrafts = Math.ceil(stillNeed / outputQty);
        const childScale = storedCrafts > 0 ? desiredCrafts / storedCrafts : 0;
        return node.ingredients.reduce((s, c) => s + computeNodeCost(c, childScale), 0);
    }

    function depthColor(depth: number): string {
        return DEPTH_COLORS[Math.min(depth, 5)];
    }
</script>

{#snippet treeRow(node: CraftNode, depth: number, scale: number)}
    {@const qty = node.qty_needed * scale}
    {@const override = nodeOverrides[node.item_id]}
    {@const isBuy = override?.mode === 'buy'}
    {@const isExpanded = override?.expanded ?? (depth < 2)}
    {@const subtotal = computeNodeCost(node, scale)}
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

        <!-- Have (inline inventory input — hidden for Labour which is not a buyable resource) -->
        <td class="py-1 px-2 text-center">
            {#if node.item_name.toLowerCase() !== LABOUR_ITEM_NAME}
                <input
                    type="number"
                    min="0"
                    value={have || ''}
                    oninput={(e) => {
                        const v = parseInt((e.target as HTMLInputElement).value);
                        onSetInventory(node.item_id, isNaN(v) ? 0 : v);
                    }}
                    class="input input-xs input-bordered w-20 text-right font-mono tabular-nums"
                    placeholder="0"
                />
            {:else}
                <span class="opacity-30 text-xs font-mono">—</span>
            {/if}
        </td>

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
            {:else if node.item_name.toLowerCase() === LABOUR_ITEM_NAME}
                <span class="badge badge-sm badge-info font-mono text-[10px]">labour</span>
            {:else}
                <span class="badge badge-sm badge-ghost font-mono text-[10px] opacity-60">raw</span>
            {/if}
        </td>

        <!-- Subtotal: show computed cost for priced/craftable nodes; '—' for unpriced leaves (e.g. Labour) -->
        <td class="text-right font-mono text-sm font-bold py-2 pr-3 tabular-nums">
            {node.unit_price != null || (node.can_craft && node.ingredients.length > 0) ? formatCurrency(subtotal) : '—'}
        </td>
    </tr>

    {#if node.can_craft && node.ingredients.length > 0 && isExpanded && !isBuy}
        {@const childStillNeed = Math.max(0, qty - have)}
        {@const childOutputQty = node.output_qty ?? 1}
        {@const storedCrafts = Math.ceil(node.qty_needed / childOutputQty)}
        {@const desiredCrafts = childStillNeed > 0 ? Math.ceil(childStillNeed / childOutputQty) : 0}
        {@const childScale = storedCrafts > 0 ? desiredCrafts / storedCrafts : 0}
        {#each node.ingredients as child}
            {@render treeRow(child, depth + 1, childScale)}
        {/each}
    {/if}
{/snippet}

<table class="w-full border-collapse text-sm">
    <thead>
        <tr class="border-b-2 border-base-200 bg-base-200/40">
            <th class="w-1 p-0"></th>
            <th class="text-left py-2 pl-4 text-xs font-mono uppercase tracking-wider opacity-60">Ingredient</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Need</th>
            <th class="text-center py-2 px-2 text-xs font-mono uppercase tracking-wider opacity-60">Have</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Still need</th>
            <th class="text-right py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Unit</th>
            <th class="py-2 pr-2 text-xs font-mono uppercase tracking-wider opacity-60">Mode</th>
            <th class="text-right py-2 pr-3 text-xs font-mono uppercase tracking-wider opacity-60">Subtotal</th>
        </tr>
    </thead>
    <tbody>
        {#each nodes as node}
            {@render treeRow(node, 1, batchSize)}
        {/each}
    </tbody>
</table>
