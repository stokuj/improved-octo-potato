<script>
    import { API_BASE_URL } from '$lib/config.js';

    /** @type {{ item: { id: number, current_price: number|null } }} */
    let { item } = $props();

    /**
     * @typedef {{
     *   item_id: number, item_name: string, qty_needed: number, unit_price: number|null,
     *   total_cost: number, can_craft: boolean, crafts_possible: number|null, ingredients: IngredientNode[]
     * }} IngredientNode
     * @typedef {{
     *   item_id: number, item_name: string, output_qty: number, multiplier: number,
     *   market_price: number|null, profit_per_craft: number|null, total_material_cost: number,
     *   ingredients: IngredientNode[]
     * }} CraftResult
     */

    let multiplier = $state(1);
    /** @type {CraftResult|null} */
    let craftTree = $state(null);
    let loading = $state(false);
    /** @type {string|null} */
    let error = $state(null);
    /** @type {boolean|null} */
    let hasRecipe = $state(null); // null=unknown, true/false after first fetch

    /** @type {Record<number, number>} */
    let inventory = $state({});

    /** @type {Set<number>} */
    let expanded = $state(new Set());

    async function calculate() {
        loading = true;
        error = null;
        try {
            const resp = await fetch(`${API_BASE_URL}/crafting/${item.id}/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ multiplier, inventory }),
            });
            if (resp.status === 404) {
                hasRecipe = false;
                return;
            }
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                error = data.detail ?? 'Calculation failed';
                return;
            }
            craftTree = await resp.json();
            hasRecipe = true;
        } catch (e) {
            error = 'Network error';
        } finally {
            loading = false;
        }
    }

    /** @param {number} itemId */
    function toggleExpand(itemId) {
        const next = new Set(expanded);
        if (next.has(itemId)) next.delete(itemId);
        else next.add(itemId);
        expanded = next;
    }

    $effect(() => {
        if (item?.id) calculate();
    });
</script>

{#if hasRecipe === false}
    <p class="text-sm opacity-50 py-4">No crafting recipe available for this item.</p>
{:else if loading && !craftTree}
    <div class="flex justify-center py-8">
        <span class="loading loading-spinner loading-md text-primary"></span>
    </div>
{:else if error}
    <div class="alert alert-error"><span>{error}</span></div>
{:else if craftTree}
    <div class="space-y-4">
        <!-- Controls -->
        <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 text-sm font-semibold">
                Crafts
                <input
                    type="number"
                    min="1"
                    bind:value={multiplier}
                    class="input input-bordered input-sm w-20"
                />
            </label>
            <button onclick={calculate} class="btn btn-sm btn-primary" disabled={loading}>
                {loading ? 'Calculating…' : 'Recalculate'}
            </button>
        </div>

        <!-- Ingredient tree -->
        <div class="overflow-x-auto">
            <table class="table table-sm w-full font-mono text-sm">
                <thead>
                    <tr class="opacity-60">
                        <th class="w-8"></th>
                        <th>Ingredient</th>
                        <th class="text-right">Need</th>
                        <th class="text-right">Have</th>
                        <th class="text-right">×Crafts</th>
                        <th class="text-right">Unit ¤</th>
                        <th class="text-right">Total ¤</th>
                    </tr>
                </thead>
                <tbody>
                    {#each craftTree.ingredients as node}
                        {@render ingredientRow(node, 0)}
                    {/each}
                </tbody>
            </table>
        </div>

        <!-- Summary -->
        <div class="divider"></div>
        <div class="flex flex-wrap gap-6 text-sm">
            <div>
                <div class="opacity-60 text-xs uppercase tracking-wide">Material Cost</div>
                <div class="font-black text-lg">{craftTree.total_material_cost.toLocaleString()} <span class="text-xs opacity-50">¤</span></div>
            </div>
            {#if craftTree.market_price != null}
                <div>
                    <div class="opacity-60 text-xs uppercase tracking-wide">Market Price ×{craftTree.output_qty * multiplier}</div>
                    <div class="font-black text-lg">{(craftTree.market_price * craftTree.output_qty * multiplier).toLocaleString()} <span class="text-xs opacity-50">¤</span></div>
                </div>
            {/if}
            {#if craftTree.profit_per_craft != null}
                <div>
                    <div class="opacity-60 text-xs uppercase tracking-wide">Profit</div>
                    <div class="font-black text-lg {craftTree.profit_per_craft >= 0 ? 'text-success' : 'text-error'}">
                        {craftTree.profit_per_craft >= 0 ? '+' : ''}{craftTree.profit_per_craft.toLocaleString()} <span class="text-xs opacity-50">¤</span>
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}

{#snippet ingredientRow(/** @type {IngredientNode} */ node, /** @type {number} */ depth)}
    <tr>
        <td style="padding-left: {depth * 1.25 + 0.5}rem">
            {#if node.can_craft}
                <button
                    class="btn btn-ghost btn-xs"
                    onclick={() => toggleExpand(node.item_id)}
                >
                    {expanded.has(node.item_id) ? '−' : '+'}
                </button>
            {:else}
                <span class="opacity-30 px-2">·</span>
            {/if}
        </td>
        <td>{node.item_name}</td>
        <td class="text-right">{node.qty_needed.toLocaleString()}</td>
        <td class="text-right">
            <input
                type="number"
                min="0"
                placeholder="0"
                value={inventory[node.item_id] ?? ''}
                oninput={(e) => {
                    const v = parseInt(/** @type {HTMLInputElement} */ (e.target).value);
                    if (!isNaN(v) && v >= 0) inventory = { ...inventory, [node.item_id]: v };
                    else {
                        const next = { ...inventory };
                        delete next[node.item_id];
                        inventory = next;
                    }
                }}
                class="input input-bordered input-xs w-24 text-right"
            />
        </td>
        <td class="text-right">
            {#if node.crafts_possible != null}
                <span class="badge badge-sm {node.crafts_possible >= 1 ? 'badge-success' : 'badge-error'}">
                    ×{node.crafts_possible}
                </span>
            {:else}
                <span class="opacity-30">—</span>
            {/if}
        </td>
        <td class="text-right opacity-60">{node.unit_price != null ? node.unit_price.toLocaleString() : '—'}</td>
        <td class="text-right font-semibold">{node.total_cost.toLocaleString()}</td>
    </tr>

    {#if node.can_craft && expanded.has(node.item_id)}
        {#each node.ingredients as child}
            {@render ingredientRow(child, depth + 1)}
        {/each}
    {/if}
{/snippet}
