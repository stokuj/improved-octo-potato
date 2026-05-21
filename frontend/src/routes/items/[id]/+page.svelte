<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { API_BASE_URL } from '$lib/config.js';
    import { getUserState } from '$lib/auth.svelte.js';
    import { gradeColor } from '$lib/grades.js';
    import { formatCurrency, splitCurrency } from '$lib/currency.js';
    import { computeNodeCost } from '$lib/crafting';
    import EChartsLineChart from '$lib/components/charts/EChartsLineChart.svelte';
    import RecipeCard from '$lib/components/crafting/RecipeCard.svelte';
    import type { ItemRead, CraftResult, CraftNode, ChartPoint, NodeOverride } from '$lib/types';

    const user = getUserState();

    const SOURCE = 'ah';
    const RANGE_OPTIONS = [
        { key: '7D',  days: 7,    interval: '1h' },
        { key: '30D', days: 30,   interval: '1h' },
        { key: '90D', days: 90,   interval: '1d' },
        { key: 'MAX', days: null, interval: '1d' },
    ];

    let selectedRange = $state('30D');

    let item: ItemRead | null = $state(null);
    let loadingItem = $state(true);
    let itemError: string | null = $state(null);

    let chartPoints: ChartPoint[] = $state([]);
    let loadingHistory = $state(false);

    let craftTree: CraftResult | null = $state(null);
    let hasRecipe: boolean | null = $state(null);

    let batchSize: number = $state(1);
    let nodeOverrides: Record<number, NodeOverride> = $state({});
    let inventory: Record<number, number> = $state({});

    const materialCost = $derived.by(() => {
        if (!craftTree) return null;
        const ctx = { inventory, nodeOverrides };
        return craftTree.ingredients.reduce((s, n) => s + computeNodeCost(n, batchSize, ctx), 0);
    });

    const profit = $derived.by(() => {
        if (materialCost == null || item == null || item.current_price == null || craftTree == null) return null;
        return item.current_price * craftTree.output_qty * batchSize - materialCost;
    });

    const margin = $derived.by(() => {
        if (profit == null || item == null || item.current_price == null || item.current_price <= 0 || craftTree == null) return null;
        return Math.round((profit / (item.current_price * craftTree.output_qty * batchSize)) * 100);
    });

    const profitPill = $derived.by(() => {
        if (materialCost == null || item == null || item.current_price == null) return null;
        return item.current_price > materialCost / ((craftTree?.output_qty ?? 1) * batchSize) ? 'above' : 'below';
    });

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

    function getItemId() { return Number(page.params.id); }
    function rangeConfig() { return RANGE_OPTIONS.find((r) => r.key === selectedRange) ?? RANGE_OPTIONS[1]; }

    function timeAgo(iso: string): string {
        const diff = Date.now() - new Date(iso).getTime();
        const m = Math.floor(diff / 60000);
        if (m < 1) return 'just now';
        if (m < 60) return `${m}m ago`;
        const h = Math.floor(m / 60);
        if (h < 24) return `${h}h ago`;
        return `${Math.floor(h / 24)}d ago`;
    }

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
                .map((row: any) => ({ t: row.bucket_start || row.captured_at, price: row.last_price ?? row.price } as ChartPoint))
                .filter((row: ChartPoint) => row.t && Number.isFinite(row.price))
                .sort((a: ChartPoint, b: ChartPoint) => new Date(a.t).getTime() - new Date(b.t).getTime());
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

            if (user.isLoggedIn) {
                try {
                    const inv = await fetch(
                        `${API_BASE_URL}/inventory/for-recipe/${getItemId()}`,
                        { credentials: 'include' }
                    );
                    if (inv.ok) {
                        const raw = await inv.json();
                        inventory = Object.fromEntries(
                            Object.entries(raw as Record<string, number>).map(([k, v]) => [Number(k), v])
                        );
                    }
                } catch { /* inventory stays empty */ }
            } else {
                inventory = {};
            }
        } catch { hasRecipe = false; }
    }

    function handleRangeChange(key: string): void {
        if (selectedRange === key) return;
        selectedRange = key;
        loadHistory();
    }

    function handleBatchChange(n: number): void { batchSize = n; }

    function handleToggleMode(id: number): void {
        const cur = nodeOverrides[id];
        nodeOverrides = { ...nodeOverrides, [id]: { mode: cur?.mode === 'buy' ? 'craft' : 'buy', expanded: cur?.expanded ?? true } };
    }

    function handleToggleExpand(id: number): void {
        const cur = nodeOverrides[id];
        nodeOverrides = { ...nodeOverrides, [id]: { mode: cur?.mode ?? 'craft', expanded: !(cur?.expanded ?? true) } };
    }

    async function handleSetInventory(itemId: number, value: number): Promise<void> {
        const prev = inventory;
        const next = { ...inventory };
        if (value > 0) next[itemId] = value;
        else delete next[itemId];
        inventory = next;

        if (!user.isLoggedIn) return;
        try {
            const resp = await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
            if (!resp.ok) {
                inventory = prev;
            }
        } catch {
            inventory = prev;
        }
    }

    onMount(async () => {
        const id = getItemId();
        if (!Number.isFinite(id) || id <= 0) {
            itemError = 'Invalid item id'; loadingItem = false; return;
        }
        await Promise.all([loadItem(), loadHistory(), loadCraftTree()]);
    });
</script>

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

    {#if loadingItem}
        <div class="flex justify-center py-24"><span class="loading loading-dots loading-lg text-primary"></span></div>
    {:else if itemError}
        <div class="alert alert-error"><span>{itemError}</span></div>
    {:else if item}

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
                            <p class="text-[10px] font-mono uppercase tracking-widest opacity-60">Profit / batch</p>
                            {#if profit != null}
                                <div class="text-4xl font-black tabular-nums" style="color:var(--color-warning)">
                                    {profit >= 0 ? '+' : ''}{formatCurrency(profit)}
                                </div>
                                <p class="text-xs font-mono opacity-60">
                                    {#if margin != null}margin {Math.max(-100, margin)}% · {/if}
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
                                {#if p.silver > 0 || p.gold > 0}<span>{p.silver.toString().padStart(2,'0')}<span class="text-slate-400 text-sm ml-0.5">s</span> </span>{/if}
                                <span>{p.bronze.toString().padStart(2,'0')}<span class="text-orange-700 text-sm ml-0.5">b</span></span>
                            </div>
                            {/if}
                        {:else}
                            <div class="text-xl font-black opacity-20 italic">No price data</div>
                        {/if}
                        {#if stats}
                            {@const statRows = [['min', stats.min], ['max', stats.max], ['avg', stats.avg], ['last', stats.last]] as [string, number][]}
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
                        <EChartsLineChart
                            points={chartPoints}
                            height={320}
                            materialCost={materialCost != null && craftTree != null
                                ? materialCost / ((craftTree.output_qty ?? 1) * batchSize)
                                : null}
                        />
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
                onSetInventory={handleSetInventory}
            />
        {/if}
    </div>
    {/if}
</div>
