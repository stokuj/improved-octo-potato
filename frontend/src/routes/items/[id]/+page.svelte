<script>
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { API_BASE_URL } from '$lib/config.js';

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

    /** @param {string} iso */
    function formatPointTime(iso) {
        const d = new Date(iso);
        if (selectedRange === '7D' || selectedRange === '30D') {
            return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
        return d.toLocaleDateString([], { year: '2-digit', month: 'short', day: 'numeric' });
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

    function getSvgData() {
        if (chartPoints.length === 0) return null;

        const width = 1000;
        const height = 280;
        const pad = 28;

        const prices = chartPoints.map((p) => p.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const ySpan = Math.max(1, maxPrice - minPrice);
        const xStep = chartPoints.length > 1 ? (width - pad * 2) / (chartPoints.length - 1) : 0;

        const points = chartPoints.map((p, i) => {
            const x = pad + i * xStep;
            const normalized = (p.price - minPrice) / ySpan;
            const y = height - pad - normalized * (height - pad * 2);
            return { ...p, x, y };
        });

        const line = points.map((p) => `${p.x},${p.y}`).join(' ');
        const area = `${pad},${height - pad} ${line} ${width - pad},${height - pad}`;

        const tickCount = Math.min(6, Math.max(2, chartPoints.length));
        const tickIndices = Array.from({ length: tickCount }, (_, i) => {
            if (tickCount === 1) return 0;
            return Math.round((i / (tickCount - 1)) * (chartPoints.length - 1));
        });

        return { width, height, pad, points, line, area, tickIndices };
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

<div class="space-y-6">
    <div class="flex items-center justify-between">
        <a href="/items" class="btn btn-ghost btn-sm">Back to items</a>
        <div class="join">
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
        <div class="card bg-base-100 border border-base-200 shadow-sm">
            <div class="card-body"><span class="loading loading-dots loading-md"></span></div>
        </div>
    {:else if itemError}
        <div class="alert alert-error"><span>{itemError}</span></div>
    {:else if item}
        {@const currentPriceParts = splitCurrency(item.current_price)}
        {@const stats = getStats()}
        {@const svg = getSvgData()}

        <div class="card bg-base-100 border border-base-200 shadow-sm">
            <div class="card-body gap-4">
                <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    <div>
                        <h1 class="text-2xl md:text-3xl font-black tracking-tight">{item.name}</h1>
                        <div class="mt-2 flex items-center gap-2">
                            <span class="badge badge-ghost badge-sm uppercase">{item.category}</span>
                            <span class="badge badge-outline badge-sm uppercase">{item.grade}</span>
                        </div>
                    </div>

                    <div class="text-right tabular-nums">
                        <div class="text-xs uppercase opacity-50 font-black">Current Price</div>
                        {#if currentPriceParts}
                            <div class="text-2xl md:text-3xl font-black mt-1">
                                {#if currentPriceParts.gold > 0}<span>{currentPriceParts.gold}<span class="text-yellow-500 text-base ml-0.5">g</span> </span>{/if}
                                {#if currentPriceParts.silver > 0 || currentPriceParts.gold > 0}<span>{currentPriceParts.silver.toString().padStart(2, '0')}<span class="text-slate-400 text-base ml-0.5">s</span> </span>{/if}
                                <span>{currentPriceParts.bronze.toString().padStart(2, '0')}<span class="text-orange-700 text-base ml-0.5">b</span></span>
                            </div>
                        {:else}
                            <div class="text-xl font-black opacity-40">--</div>
                        {/if}
                        <div class="text-xs opacity-40 mt-1">Updated {new Date(item.updated_at).toLocaleString()}</div>
                    </div>
                </div>

                <div class="rounded-box border border-base-200 bg-base-50 p-3 md:p-4">
                    {#if loadingHistory}
                        <div class="h-64 flex items-center justify-center"><span class="loading loading-dots loading-lg"></span></div>
                    {:else if historyError}
                        <div class="alert alert-error"><span>{historyError}</span></div>
                    {:else if chartPoints.length === 0 || !svg}
                        <div class="h-64 flex flex-col items-center justify-center text-center opacity-60 gap-2">
                            <span class="font-bold">No price history for this range</span>
                            <span class="text-xs uppercase">Source: {SOURCE}</span>
                        </div>
                    {:else}
                        <div class="w-full overflow-x-auto">
                            <svg viewBox={`0 0 ${svg.width} ${svg.height}`} class="w-full min-w-[640px] h-64" role="img" aria-label="Price history chart">
                                <polyline points={svg.area} fill="oklch(var(--p) / 0.12)" stroke="none" />
                                <polyline points={svg.line} fill="none" stroke="oklch(var(--p))" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                                {#each svg.tickIndices as idx}
                                    {@const point = svg.points[idx]}
                                    <line x1={point.x} y1={svg.height - svg.pad + 2} x2={point.x} y2={svg.height - svg.pad + 8} stroke="oklch(var(--bc) / 0.25)" />
                                    <text x={point.x} y={svg.height - 6} text-anchor="middle" class="fill-base-content/50 text-[11px]">{formatPointTime(point.t)}</text>
                                {/each}
                            </svg>
                        </div>
                    {/if}
                </div>

                {#if stats}
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
                        <div class="stat bg-base-200/60 rounded-box p-3">
                            <div class="stat-title text-[10px] uppercase">Min</div>
                            <div class="stat-value text-base md:text-lg">{formatCurrency(stats.min)}</div>
                        </div>
                        <div class="stat bg-base-200/60 rounded-box p-3">
                            <div class="stat-title text-[10px] uppercase">Average</div>
                            <div class="stat-value text-base md:text-lg">{formatCurrency(stats.avg)}</div>
                        </div>
                        <div class="stat bg-base-200/60 rounded-box p-3">
                            <div class="stat-title text-[10px] uppercase">Max</div>
                            <div class="stat-value text-base md:text-lg">{formatCurrency(stats.max)}</div>
                        </div>
                        <div class="stat bg-base-200/60 rounded-box p-3">
                            <div class="stat-title text-[10px] uppercase">Last</div>
                            <div class="stat-value text-base md:text-lg">{formatCurrency(stats.last)}</div>
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>
