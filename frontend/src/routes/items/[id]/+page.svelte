<script>
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { API_BASE_URL } from '$lib/config.js';
    import EChartsLineChart from '$lib/components/charts/EChartsLineChart.svelte';

    /** @typedef {{ id: number, name: string, category: string, grade: string, current_price: number | null, updated_at: string }} ItemDetail */
    /** @typedef {{ t: string, price: number }} ChartPoint */

    const SOURCE = 'market';

    const RANGE_OPTIONS = [
        { key: '7D', days: 7, interval: '1h' },
        { key: '30D', days: 30, interval: '1h' },
        { key: '90D', days: 90, interval: '1d' },
        { key: 'MAX', days: null, interval: '1d' }
    ];

    let selectedRange = $state('30D');

    /** @type {ItemDetail | null} */
    let item = $state(null);
    let loadingItem = $state(true);
    /** @type {string | null} */
    let itemError = $state(null);

    /** @type {ChartPoint[]} */
    let chartPoints = $state([]);
    let loadingHistory = $state(true);
    /** @type {string | null} */
    let historyError = $state(null);

    function selectedConfig() {
        return RANGE_OPTIONS.find((r) => r.key === selectedRange) || RANGE_OPTIONS[1];
    }

    function getItemId() {
        return Number(page.params.id);
    }

    async function loadItem() {
        loadingItem = true;
        itemError = null;

        try {
            const response = await fetch(`${API_BASE_URL}/items/${getItemId()}`);
            if (!response.ok) {
                itemError = `Could not load item (${response.status})`;
                return;
            }
            item = await response.json();
        } catch (e) {
            console.error('Error loading item:', e);
            itemError = 'Network error while loading item';
        } finally {
            loadingItem = false;
        }
    }

    async function loadHistory() {
        loadingHistory = true;
        historyError = null;

        try {
            const cfg = selectedConfig();
            const params = new URLSearchParams({
                source: SOURCE,
                interval: cfg.interval
            });

            if (cfg.days !== null) {
                const from = new Date();
                from.setDate(from.getDate() - cfg.days);
                params.append('from', from.toISOString());
            }
            params.append('to', new Date().toISOString());

            const response = await fetch(`${API_BASE_URL}/items/${getItemId()}/price-history?${params.toString()}`);
            if (!response.ok) {
                historyError = `Could not load price history (${response.status})`;
                chartPoints = [];
                return;
            }

            /** @type {any[]} */
            const data = await response.json();
            chartPoints = data
                .map((row) => ({
                    t: row.bucket_start || row.captured_at,
                    price: row.last_price ?? row.price
                }))
                .filter((row) => row.t && Number.isFinite(row.price))
                .sort((a, b) => new Date(a.t).getTime() - new Date(b.t).getTime());
        } catch (e) {
            console.error('Error loading history:', e);
            historyError = 'Network error while loading history';
            chartPoints = [];
        } finally {
            loadingHistory = false;
        }
    }

    /** @param {string} rangeKey */
    function handleRangeChange(rangeKey) {
        if (selectedRange === rangeKey) return;
        selectedRange = rangeKey;
        loadHistory();
    }

    /** @param {number | null | undefined} totalBronze */
    function splitCurrency(totalBronze) {
        if (!totalBronze && totalBronze !== 0) return null;
        const gold = Math.floor(totalBronze / 10000);
        const silver = Math.floor((totalBronze % 10000) / 100);
        const bronze = totalBronze % 100;
        return { gold, silver, bronze };
    }

    /** @param {number | null | undefined} totalBronze */
    function formatCurrency(totalBronze) {
        const c = splitCurrency(totalBronze);
        if (!c) return '--';
        const gold = c.gold > 0 ? `${c.gold}g ` : '';
        const silver = c.silver > 0 || c.gold > 0 ? `${c.silver.toString().padStart(2, '0')}s ` : '';
        const bronze = `${c.bronze.toString().padStart(2, '0')}b`;
        return `${gold}${silver}${bronze}`.trim();
    }

    function getStats() {
        if (chartPoints.length === 0) return null;
        const prices = chartPoints.map((p) => p.price);
        const min = Math.min(...prices);
        const max = Math.max(...prices);
        const last = prices[prices.length - 1];
        const avg = Math.round(prices.reduce((sum, n) => sum + n, 0) / prices.length);
        return { min, max, avg, last };
    }

    onMount(async () => {
        const itemId = getItemId();
        if (!Number.isFinite(itemId) || itemId <= 0) {
            itemError = 'Invalid item id';
            loadingItem = false;
            loadingHistory = false;
            return;
        }

        await Promise.all([loadItem(), loadHistory()]);
    });
</script>

<div class="space-y-6 max-w-7xl mx-auto px-4 py-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <a href="/items" class="btn btn-ghost btn-sm flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
            Back to items
        </a>
        <div class="join shadow-sm border border-base-200">
            {#each RANGE_OPTIONS as option}
                <button
                    class="btn btn-sm join-item {selectedRange === option.key ? 'btn-primary' : 'btn-ghost'}"
                    onclick={() => handleRangeChange(option.key)}
                >
                    {option.key}
                </button>
            {/each}
        </div>
    </div>

    {#if loadingItem}
        <div class="h-96 flex items-center justify-center">
            <span class="loading loading-dots loading-lg text-primary"></span>
        </div>
    {:else if itemError}
        <div class="alert alert-error shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>{itemError}</span>
        </div>
    {:else if item}
        {@const currentPriceParts = splitCurrency(item.current_price)}
        {@const stats = getStats()}

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Left Panel: Item Info -->
            <div class="lg:col-span-1 space-y-6">
                <div class="card bg-base-100 border border-base-200 shadow-sm">
                    <div class="card-body p-6">
                        <div class="space-y-1">
                            <h1 class="text-2xl font-black tracking-tight">{item.name}</h1>
                            <div class="flex flex-wrap gap-2 pt-1">
                                <span class="badge badge-ghost badge-xs uppercase font-bold opacity-60 tracking-tighter">{item.category}</span>
                                <span class="badge badge-outline badge-xs uppercase font-bold opacity-60 tracking-tighter">{item.grade}</span>
                            </div>
                        </div>

                        <div class="divider my-4"></div>

                        <div class="space-y-4">
                            <div>
                                <div class="text-[10px] uppercase font-black opacity-30 tracking-widest mb-1">Current Price</div>
                                {#if currentPriceParts}
                                    <div class="text-2xl font-black tabular-nums tracking-tight">
                                        {#if currentPriceParts.gold > 0}<span>{currentPriceParts.gold}<span class="text-yellow-500 text-sm ml-0.5">G</span> </span>{/if}
                                        {#if currentPriceParts.silver > 0 || currentPriceParts.gold > 0}<span>{currentPriceParts.silver.toString().padStart(2, '0')}<span class="text-slate-400 text-sm ml-0.5">S</span> </span>{/if}
                                        <span>{currentPriceParts.bronze.toString().padStart(2, '0')}<span class="text-orange-700 text-sm ml-0.5">B</span></span>
                                    </div>
                                {:else}
                                    <div class="text-xl font-black opacity-20 italic">No price data</div>
                                {/if}
                                <div class="text-[10px] opacity-40 mt-1 uppercase font-bold">Updated: {new Date(item.updated_at).toLocaleString()}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Simple Stats Grid -->
                {#if stats}
                    <div class="grid grid-cols-2 gap-4">
                        <div class="card bg-base-100 border border-base-200 shadow-sm">
                            <div class="card-body p-4 gap-0">
                                <div class="text-[10px] uppercase font-black opacity-30 mb-1">Min</div>
                                <div class="text-sm font-black tabular-nums truncate">{formatCurrency(stats.min)}</div>
                            </div>
                        </div>
                        <div class="card bg-base-100 border border-base-200 shadow-sm">
                            <div class="card-body p-4 gap-0">
                                <div class="text-[10px] uppercase font-black opacity-30 mb-1">Max</div>
                                <div class="text-sm font-black tabular-nums truncate">{formatCurrency(stats.max)}</div>
                            </div>
                        </div>
                        <div class="card bg-base-100 border border-base-200 shadow-sm">
                            <div class="card-body p-4 gap-0">
                                <div class="text-[10px] uppercase font-black opacity-30 mb-1">Avg</div>
                                <div class="text-sm font-black tabular-nums truncate">{formatCurrency(stats.avg)}</div>
                            </div>
                        </div>
                        <div class="card bg-base-100 border border-base-200 shadow-sm">
                            <div class="card-body p-4 gap-0">
                                <div class="text-[10px] uppercase font-black opacity-30 mb-1">Last</div>
                                <div class="text-sm font-black tabular-nums truncate">{formatCurrency(stats.last)}</div>
                            </div>
                        </div>
                    </div>
                {/if}
            </div>

            <!-- Right Panel: Chart -->
            <div class="lg:col-span-3 space-y-6">
                <div class="card bg-base-100 border border-base-200 shadow-sm overflow-hidden h-full">
                    <div class="card-body p-0 gap-0 h-full">
                        <div class="flex items-center justify-between px-6 py-4 border-b border-base-200 bg-base-200/20">
                            <div class="flex items-center gap-2">
                                <h2 class="font-black text-xs uppercase tracking-widest opacity-60">Price History</h2>
                                <div class="badge badge-primary badge-outline badge-xs font-black uppercase">{selectedRange}</div>
                            </div>
                            <div class="text-[10px] font-bold uppercase opacity-30">Source: {SOURCE}</div>
                        </div>

                        <div class="p-6 h-full min-h-[450px]">
                            {#if loadingHistory}
                                <div class="h-full flex items-center justify-center">
                                    <span class="loading loading-spinner loading-lg text-primary"></span>
                                </div>
                            {:else if historyError}
                                <div class="alert alert-error shadow-sm">
                                    <span>{historyError}</span>
                                </div>
                            {:else if chartPoints.length === 0}
                                <div class="h-full flex flex-col items-center justify-center text-center opacity-30 py-20 gap-3">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>
                                    <span class="font-black uppercase tracking-widest text-[10px]">No historical data found for this range</span>
                                </div>
                            {:else}
                                <EChartsLineChart points={chartPoints} height={400} />
                            {/if}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>
