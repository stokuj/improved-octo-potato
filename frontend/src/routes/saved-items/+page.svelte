<script>
    import { user } from '$lib/auth.svelte.js';
    import { goto } from '$app/navigation';

    // Mock data for "Saved Items" - items tracked by the user
    let myItems = $state([
        { 
            id: 101, 
            name: "Luxurious Royal Sword", 
            currentPrice: 1250000, // 125g
            oldPrice: 1100000, 
            change: 13.6,
            lastUpdate: "2 minutes ago",
            rarity: "Legendary"
        },
        { 
            id: 102, 
            name: "Dragon Glow Shield", 
            currentPrice: 84000, // 8g 40s
            oldPrice: 92000, 
            change: -8.7,
            lastUpdate: "15 minutes ago",
            rarity: "Rare"
        },
        { 
            id: 103, 
            name: "Greater Power Potion", 
            currentPrice: 450, // 4s 50b
            oldPrice: 450, 
            change: 0,
            lastUpdate: "1 hour ago",
            rarity: "Common"
        }
    ]);

    // Redirect if not logged in
    $effect(() => {
        if (!user.loading && !user.isLoggedIn) {
            goto('/auth');
        }
    });

    // Currency helper
    function splitCurrency(totalBronze) {
        if (!totalBronze && totalBronze !== 0) return null;
        const gold = Math.floor(totalBronze / 10000);
        const silver = Math.floor((totalBronze % 10000) / 100);
        const bronze = totalBronze % 100;
        return { gold, silver, bronze };
    }
</script>

<div class="space-y-6">
    <div class="flex justify-between items-end border-b border-base-300 pb-4">
        <div>
            <h1 class="text-3xl font-black text-primary uppercase tracking-tighter">Saved Items</h1>
            <p class="text-base-content/60 font-medium">Monitoring your chosen market items</p>
        </div>
        <div class="stats shadow bg-base-200 hidden md:flex border border-base-300">
            <div class="stat py-2 px-6">
                <div class="stat-title text-[10px] uppercase font-bold opacity-50">Tracked</div>
                <div class="stat-value text-2xl text-primary font-black">{myItems.length}</div>
            </div>
            <div class="stat py-2 px-6">
                <div class="stat-title text-[10px] uppercase font-bold opacity-50">Est. Value</div>
                <div class="stat-value text-2xl text-secondary font-black">~134g</div>
            </div>
        </div>
    </div>

    {#if !user.isLoggedIn}
        <div class="hero bg-base-200 rounded-box p-10 border border-base-300">
            <div class="hero-content text-center">
                <div class="max-w-md">
                    <h2 class="text-3xl font-black">Sign in to track prices</h2>
                    <p class="py-6 text-base-content/70">Only logged in users can add items to their saved items list and monitor changes in real-time.</p>
                    <a href="/auth" class="btn btn-primary btn-wide shadow-lg">Go to Login</a>
                </div>
            </div>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each myItems as item}
                {@const c = splitCurrency(item.currentPrice)}
                <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all border border-base-200 group overflow-hidden">
                    <div class="card-body p-6">
                        <div class="flex justify-between items-start mb-4">
                            <span class="badge badge-sm badge-outline opacity-50 font-medium border-base-content/20 uppercase tracking-wider">{item.rarity}</span>
                            <button class="btn btn-ghost btn-xs text-error opacity-40 hover:opacity-100 transition-opacity font-bold uppercase tracking-widest">Remove</button>
                        </div>
                        
                        <h2 class="card-title text-xl font-bold leading-tight mb-6 group-hover:text-primary transition-colors">{item.name}</h2>
                        
                        <div class="bg-base-200/50 p-4 rounded-xl border border-base-300/50">
                            <div class="flex items-center justify-between mb-2">
                                <span class="text-[10px] uppercase opacity-40 font-black tracking-widest">Market Price</span>
                                <div class="text-right">
                                    <div class="flex items-center gap-1 font-bold text-xs {item.change > 0 ? 'text-error' : item.change < 0 ? 'text-success' : ''}">
                                        {#if item.change !== 0}
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                                                {#if item.change > 0}
                                                    <path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
                                                {:else}
                                                    <path fill-rule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1V9a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586 3.707 5.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L11 9.414 14.586 13H12z" clip-rule="evenodd" />
                                                {/if}
                                            </svg>
                                        {/if}
                                        {item.change > 0 ? '+' : ''}{item.change}%
                                    </div>
                                </div>
                            </div>

                            <div class="flex items-center gap-3 font-black text-2xl tabular-nums">
                                {#if c.gold > 0}
                                    <span class="flex items-center gap-0.5">
                                        {c.gold}<span class="text-yellow-500 font-bold text-sm uppercase">g</span>
                                    </span>
                                {/if}
                                {#if c.silver > 0 || c.gold > 0}
                                    <span class="flex items-center gap-0.5">
                                        {c.silver.toString().padStart(2, '0')}<span class="text-slate-400 font-bold text-sm uppercase">s</span>
                                    </span>
                                {/if}
                                <span class="flex items-center gap-0.5">
                                    {c.bronze.toString().padStart(2, '0')}<span class="text-orange-700 font-bold text-sm uppercase">b</span>
                                </span>
                            </div>
                        </div>

                        <div class="flex justify-between items-center mt-6">
                            <span class="text-[10px] uppercase opacity-30 font-bold tracking-tighter">Updated: {item.lastUpdate}</span>
                            <a href="/items/{item.id}" class="btn btn-sm btn-outline border-base-300 font-black uppercase text-[10px] tracking-widest">Details</a>
                        </div>
                    </div>
                </div>
            {/each}
            
            <button class="btn btn-outline border-dashed border-2 h-full min-h-[220px] flex flex-col gap-3 hover:bg-primary/5 hover:border-primary transition-all group">
                <div class="p-4 rounded-full bg-base-200 group-hover:bg-primary/10 transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 opacity-20 group-hover:opacity-100 group-hover:text-primary transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                </div>
                <span class="text-base-content/30 uppercase font-black text-[10px] tracking-[0.2em] group-hover:text-primary transition-colors">Track New Item</span>
            </button>
        </div>
    {/if}
</div>
