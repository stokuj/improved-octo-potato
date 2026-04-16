<script>
    import { user } from '$lib/auth.svelte.js';
    import { goto } from '$app/navigation';

    // Mock data for "Saved Items" - items tracked by the user
    let myItems = $state([
        { 
            id: 101, 
            name: "Luxurious Royal Sword", 
            currentPrice: 12500, 
            oldPrice: 11000, 
            change: 13.6,
            lastUpdate: "2 minutes ago",
            rarity: "Legendary"
        },
        { 
            id: 102, 
            name: "Dragon Glow Shield", 
            currentPrice: 8400, 
            oldPrice: 9200, 
            change: -8.7,
            lastUpdate: "15 minutes ago",
            rarity: "Rare"
        },
        { 
            id: 103, 
            name: "Greater Power Potion", 
            currentPrice: 450, 
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
</script>

<div class="space-y-6">
    <div class="flex justify-between items-end border-b border-base-300 pb-4">
        <div>
            <h1 class="text-3xl font-black text-primary">Saved Items</h1>
            <p class="text-base-content/60">Tracked item prices from Item House</p>
        </div>
        <div class="stats shadow bg-base-200 hidden md:flex">
            <div class="stat py-2 px-4">
                <div class="stat-title text-xs uppercase">Tracked</div>
                <div class="stat-value text-lg text-primary">{myItems.length}</div>
            </div>
            <div class="stat py-2 px-4">
                <div class="stat-title text-xs uppercase">Value</div>
                <div class="stat-value text-lg text-secondary">~21.3k</div>
            </div>
        </div>
    </div>

    {#if !user.isLoggedIn}
        <div class="hero bg-base-200 rounded-box p-10">
            <div class="hero-content text-center">
                <div class="max-w-md">
                    <h2 class="text-2xl font-bold">Sign in to track prices</h2>
                    <p class="py-4 text-base-content/70">Only logged in users can add items to their saved items list and monitor changes.</p>
                    <a href="/auth" class="btn btn-primary">Go to Login</a>
                </div>
            </div>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each myItems as item}
                <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all border border-base-200 group">
                    <div class="card-body p-5">
                        <div class="flex justify-between items-start mb-2">
                            <span class="badge badge-sm font-bold {
                                item.rarity === 'Legendary' ? 'badge-warning' : 
                                item.rarity === 'Rare' ? 'badge-info' : 'badge-ghost'
                            }">{item.rarity}</span>
                            <button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity">Remove</button>
                        </div>
                        
                        <h2 class="card-title text-lg leading-tight mb-4">{item.name}</h2>
                        
                        <div class="flex items-center justify-between bg-base-200/50 p-3 rounded-lg">
                            <div>
                                <div class="text-xs uppercase opacity-50 font-bold">Price</div>
                                <div class="text-xl font-black">{item.currentPrice.toLocaleString()} <span class="text-xs font-normal">silver</span></div>
                            </div>
                            <div class="text-right">
                                <div class="text-xs uppercase opacity-50 font-bold">Change</div>
                                <div class="flex items-center gap-1 font-bold {item.change > 0 ? 'text-error' : item.change < 0 ? 'text-success' : ''}">
                                    {#if item.change > 0}
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
                                        </svg>
                                    {:else if item.change < 0}
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1V9a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586 3.707 5.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L11 9.414 14.586 13H12z" clip-rule="evenodd" />
                                        </svg>
                                    {/if}
                                    {item.change > 0 ? '+' : ''}{item.change}%
                                </div>
                            </div>
                        </div>

                        <div class="card-actions justify-between items-center mt-4">
                            <span class="text-[10px] uppercase opacity-40 font-bold">Update: {item.lastUpdate}</span>
                            <a href="/items/{item.id}" class="btn btn-sm btn-ghost border border-base-300">Details</a>
                        </div>
                    </div>
                </div>
            {/each}
            
            <!-- Placeholder Card for adding new -->
            <button class="btn btn-outline border-dashed border-2 h-full min-h-[180px] flex flex-col gap-2 hover:bg-primary/5 hover:border-primary">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                <span class="text-base-content/40 uppercase font-black text-xs tracking-widest">Add Item</span>
            </button>
        </div>
    {/if}
</div>
