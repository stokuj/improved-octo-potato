<script>
    import { API_BASE_URL } from '$lib/config.js';

    let items = $state([]);
    let loading = $state(true);
    let error = $state(null);

    async function loadHotItems() {
        try {
            const resp = await fetch(`${API_BASE_URL}/items/?limit=3`);
            if (!resp.ok) throw new Error('Failed to fetch items');
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

<div class="space-y-12">
    <!-- Hero section -->
    <section class="hero bg-gradient-to-br from-base-200 to-base-300 rounded-box p-12 shadow-inner overflow-hidden relative">
        <div class="absolute -right-20 -top-20 w-64 h-64 bg-primary/10 rounded-full blur-3xl"></div>
        <div class="absolute -left-20 -bottom-20 w-64 h-64 bg-secondary/10 rounded-full blur-3xl"></div>

        <div class="hero-content text-center relative z-10">
            <div class="max-w-2xl">
                <h1 class="text-6xl font-black text-primary tracking-tighter">AA Tracker <span class="text-base-content">Svelte</span></h1>
                <p class="py-6 text-xl text-base-content/70 font-medium">
                    The fastest item price tracker from <span class="text-secondary font-bold">Item House</span>. Monitor the market, track changes, and optimize your inventory.
                </p>
                <div class="flex gap-4 justify-center">
                    <a href="/items" class="btn btn-primary btn-lg shadow-xl hover:scale-105 transition-all">Browse Market</a>
                    <a href="/auth" class="btn btn-outline btn-lg hover:scale-105 transition-all">Join Us</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Market Overview -->
    <section class="space-y-4">
        <div class="flex justify-between items-center px-2">
            <h2 class="text-2xl font-black uppercase tracking-widest opacity-80">Hot Deals</h2>
            <a href="/items" class="link link-primary no-underline font-bold text-sm">See all &rarr;</a>
        </div>

        {#if loading}
            <div class="flex justify-center py-12">
                <span class="loading loading-spinner loading-lg text-primary"></span>
            </div>
        {:else if error}
            <div class="alert alert-error">
                <span>{error}</span>
            </div>
        {:else if items.length === 0}
            <div class="text-center py-12 opacity-50">No items found.</div>
        {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {#each items as item}
                    <a href="/items/{item.id}" class="card bg-base-100 shadow-md border border-base-200 hover:border-primary/50 transition-all cursor-pointer overflow-hidden">
                        <div class="card-body p-6">
                            <div class="flex justify-between items-start">
                                <h3 class="card-title text-primary">{item.name}</h3>
                                <div class="badge badge-ghost badge-sm font-bold">{item.grade}</div>
                            </div>
                            <p class="text-sm opacity-60 italic">{item.category}</p>
                            <div class="divider my-1 opacity-20"></div>
                            <div class="flex justify-between items-end">
                                <div class="text-2xl font-black text-secondary">
                                    {item.current_price != null ? item.current_price.toLocaleString() : '—'}
                                    <span class="text-xs font-normal opacity-50">silver</span>
                                </div>
                                <button class="btn btn-xs btn-primary btn-outline">Track</button>
                            </div>
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    </section>
</div>
