<script>
    import { API_BASE_URL } from '$lib/config.js';
    import { gradeColor } from '$lib/grades.js';

    /** @type {any[]} */
    let items = $state([]);
    let loading = $state(true);
    /** @type {string|null} */
    let error = $state(null);

    async function loadHotItems() {
        try {
            const resp = await fetch(`${API_BASE_URL}/items/?limit=3`);
            if (!resp.ok) throw new Error('Failed to fetch');
            const data = await resp.json();
            items = data.items;
        } catch (e) {
            error = 'Could not load items.';
        } finally {
            loading = false;
        }
    }

    loadHotItems();
</script>

<div class="space-y-10">
    <!-- Hero -->
    <section class="relative overflow-hidden rounded-box bg-gradient-to-br from-base-200 via-base-200 to-primary/10 border border-base-300/50 shadow-inner">
        <div class="absolute inset-0 pointer-events-none">
            <div class="absolute -right-24 -top-24 w-72 h-72 bg-primary/8 rounded-full blur-3xl"></div>
            <div class="absolute -left-24 -bottom-24 w-72 h-72 bg-secondary/8 rounded-full blur-3xl"></div>
            <!-- Grade color dots for atmosphere -->
            <div class="absolute top-6 right-1/4 w-1 h-1 rounded-full opacity-60" style="background: var(--grade-celestial); box-shadow: 0 0 12px var(--grade-celestial);"></div>
            <div class="absolute top-12 right-1/3 w-1.5 h-1.5 rounded-full opacity-40" style="background: var(--grade-heroic); box-shadow: 0 0 10px var(--grade-heroic);"></div>
            <div class="absolute bottom-10 left-1/4 w-1 h-1 rounded-full opacity-50" style="background: var(--grade-mythic); box-shadow: 0 0 10px var(--grade-mythic);"></div>
            <div class="absolute top-8 left-1/3 w-2 h-2 rounded-full opacity-30" style="background: var(--grade-unique); box-shadow: 0 0 14px var(--grade-unique);"></div>
        </div>

        <div class="relative z-10 text-center py-16 px-6 max-w-2xl mx-auto">
            <div class="flex justify-center gap-2 mb-4">
                {#each ['Grand','Rare','Arcane','Heroic','Unique','Celestial','Legendary'] as g}
                    <span class="w-2 h-2 rounded-full opacity-70" style="background: {gradeColor(g)}; box-shadow: 0 0 6px {gradeColor(g)};"></span>
                {/each}
            </div>
            <h1 class="text-5xl sm:text-6xl font-black tracking-tighter text-base-content mb-2">
                <span class="text-primary">AA</span> Tracker
            </h1>
            <p class="text-base-content/50 text-sm font-black uppercase tracking-widest mb-6">
                ArcheAge Market Price Monitor
            </p>
            <p class="text-base-content/70 text-lg mb-8 max-w-lg mx-auto leading-relaxed">
                Track item prices, monitor market trends, and calculate crafting profits in real time.
            </p>
            <div class="flex gap-3 justify-center flex-wrap">
                <a href="/items" class="btn btn-primary btn-lg shadow-lg shadow-primary/20 font-bold">
                    Browse Market
                </a>
                <a href="/auth" class="btn btn-outline btn-lg font-bold">
                    Create Account
                </a>
            </div>
        </div>
    </section>

    <!-- Hot Deals -->
    <section class="space-y-4">
        <div class="flex justify-between items-center px-1">
            <h2 class="text-xs font-black uppercase tracking-widest opacity-40">Hot Deals</h2>
            <a href="/items" class="text-xs font-black uppercase tracking-widest text-primary hover:opacity-70 transition-opacity">
                See all →
            </a>
        </div>

        {#if loading}
            <div class="flex justify-center py-12">
                <span class="loading loading-spinner loading-lg text-primary"></span>
            </div>
        {:else if error}
            <div class="alert alert-error"><span>{error}</span></div>
        {:else if items.length === 0}
            <div class="text-center py-12 opacity-30">No items found.</div>
        {:else}
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {#each items as item}
                    {@const c = gradeColor(item.grade)}
                    <a
                        href="/items/{item.id}"
                        class="card bg-base-200 border hover:border-opacity-60 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 overflow-hidden"
                        style="border-color: {c}30;"
                    >
                        <div class="card-body p-5 gap-3">
                            <div class="flex justify-between items-start gap-2">
                                <h3 class="font-black text-base leading-tight">{item.name}</h3>
                                <span
                                    class="badge badge-outline badge-xs font-black uppercase shrink-0"
                                    style="color: {c}; border-color: {c}55;"
                                >
                                    {item.grade}
                                </span>
                            </div>
                            <p class="text-xs opacity-40 uppercase font-bold tracking-wide">{item.category}</p>
                            <div class="flex justify-between items-end pt-1 border-t border-base-300/50">
                                <div class="text-xl font-black tabular-nums" style="color: {c};">
                                    {item.current_price != null ? item.current_price.toLocaleString() : '—'}
                                    <span class="text-xs font-normal opacity-40 ml-0.5">¤</span>
                                </div>
                                <span class="text-xs opacity-30 font-bold uppercase">View →</span>
                            </div>
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    </section>

    <!-- Feature strip -->
    <section class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        {#each [
            { icon: '📈', title: 'Price History', desc: '30 days of market data with 1h/1d interval charts' },
            { icon: '⭐', title: 'Watchlist', desc: 'Save items and monitor your portfolio in one place' },
            { icon: '⚗️', title: 'Craft Calculator', desc: 'Calculate costs, profit margins, and nested recipes' }
        ] as f}
            <div class="bg-base-200/50 border border-base-300/40 rounded-box p-5 flex gap-4 items-start">
                <span class="text-2xl">{f.icon}</span>
                <div>
                    <div class="font-black text-sm mb-1">{f.title}</div>
                    <div class="text-xs opacity-50 leading-relaxed">{f.desc}</div>
                </div>
            </div>
        {/each}
    </section>
</div>
