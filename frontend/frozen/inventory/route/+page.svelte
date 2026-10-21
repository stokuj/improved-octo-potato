<!-- frontend/src/routes/inventory/+page.svelte -->
<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { API_BASE_URL } from '$lib/config.js';
    import { getUserState } from '$lib/auth.svelte.js';
    import { gradeColor } from '$lib/grades.js';
    import type { ItemListItem, InventoryItem } from '$lib/types';

    const user = getUserState();

    const CATEGORIES = [
        'Special Product','Weapons','Armor','Accessories','Instrument',
        'Costume','Consumables','Crafting','Machining','Companions',
        'Other','Lunagem','Lunastone'
    ];
    const GRADES = [
        'Basic','Grand','Rare','Arcane','Heroic','Unique',
        'Celestial','Divine','Epic','Legendary','Mythic','Eternal'
    ];

    let allItems: ItemListItem[] = $state([]);
    let quantities: Record<number, number> = $state({});
    let loading = $state(true);
    let searchQuery = $state('');
    let selectedCategory = $state('');
    let selectedGrade = $state('');

    let saveError: string | null = $state(null);

    let debounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};
    // Plain (non-reactive) guard — prevents double-call if $effect re-evaluates before load completes
    let dataLoadStarted = false;

    const filtered = $derived.by(() => {
        return allItems.filter(item => {
            if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
            if (selectedCategory && item.category !== selectedCategory) return false;
            if (selectedGrade && item.grade !== selectedGrade) return false;
            return true;
        });
    });

    async function loadData() {
        loading = true;
        try {
            // Fetch inventory and first items page in parallel
            const [firstPageResp, invResp] = await Promise.all([
                fetch(`${API_BASE_URL}/items/?limit=200&offset=0`, { credentials: 'include' }),
                fetch(`${API_BASE_URL}/inventory/`, { credentials: 'include' }),
            ]);
            if (!firstPageResp.ok) return;
            if (invResp.status === 401) { goto('/auth'); return; }
            if (!invResp.ok) return;

            const firstPage = await firstPageResp.json();
            const collected: ItemListItem[] = [...(firstPage.items ?? [])];
            const total = firstPage.total ?? 0;

            // Fetch remaining pages sequentially
            let offset = 200;
            while (collected.length < total) {
                const resp = await fetch(`${API_BASE_URL}/items/?limit=200&offset=${offset}`, { credentials: 'include' });
                if (!resp.ok) break;
                const page = await resp.json();
                collected.push(...(page.items ?? []));
                offset += 200;
            }

            const inv = await invResp.json() as InventoryItem[];
            allItems = collected;
            quantities = Object.fromEntries(inv.map((r) => [r.item_id, r.quantity]));
        } finally {
            loading = false;
        }
    }

    function handleQuantityChange(itemId: number, value: number) {
        quantities = { ...quantities, [itemId]: value };
        saveError = null;
        clearTimeout(debounceTimers[itemId]);
        debounceTimers[itemId] = setTimeout(async () => {
            try {
                const resp = await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ quantity: value }),
                });
                if (!resp.ok) saveError = 'Failed to save quantity. Please refresh.';
            } catch {
                saveError = 'Failed to save quantity. Please refresh.';
            }
        }, 400);
    }

    onMount(() => {
        if (!user.loading && !user.isLoggedIn) {
            goto('/auth');
        }
    });

    $effect(() => {
        if (user.loading) return;
        if (!user.isLoggedIn) { goto('/auth'); return; }
        if (!dataLoadStarted) {
            dataLoadStarted = true;
            loadData();
        }
    });
</script>

<div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <h1 class="text-2xl font-black tracking-tight">Inventory</h1>

    <!-- Filter bar -->
    <div class="flex flex-col md:flex-row gap-3 sticky top-16 z-10 bg-base-100/80 py-2 backdrop-blur-sm">
        <input
            type="text"
            placeholder="Search items…"
            bind:value={searchQuery}
            class="input input-bordered input-sm md:input-md w-full md:w-64"
        />
        <select class="select select-bordered select-sm md:select-md w-full md:min-w-[180px]" bind:value={selectedCategory}>
            <option value="">All Categories</option>
            {#each CATEGORIES as cat}<option value={cat}>{cat}</option>{/each}
        </select>
        <select class="select select-bordered select-sm md:select-md w-full md:min-w-[150px]" bind:value={selectedGrade}>
            <option value="">All Grades</option>
            {#each GRADES as g}<option value={g}>{g}</option>{/each}
        </select>
    </div>

    {#if loading}
        <div class="flex justify-center py-20">
            <span class="loading loading-dots loading-lg text-primary"></span>
        </div>
    {:else}
        {#if saveError}
            <div class="alert alert-error mb-4">
                <span>{saveError}</span>
            </div>
        {/if}
        <div class="card bg-base-100 border border-base-200 shadow-sm overflow-x-auto">
            <table class="table table-sm w-full">
                <thead>
                    <tr class="bg-base-200/50">
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Item</th>
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Category</th>
                        <th class="text-xs font-mono uppercase tracking-wider opacity-60">Grade</th>
                        <th class="text-right text-xs font-mono uppercase tracking-wider opacity-60">Quantity</th>
                    </tr>
                </thead>
                <tbody>
                    {#each filtered as item (item.id)}
                        <tr class="hover:bg-base-200/30">
                            <td class="font-medium">{item.name}</td>
                            <td class="text-xs opacity-60">{item.category}</td>
                            <td>
                                <span class="badge badge-outline badge-xs font-black uppercase"
                                      style="color:{gradeColor(item.grade)};border-color:{gradeColor(item.grade)}55">
                                    {item.grade}
                                </span>
                            </td>
                            <td class="text-right">
                                <input
                                    type="number"
                                    min="0"
                                    value={quantities[item.id] ?? ''}
                                    placeholder="0"
                                    oninput={(e) => {
                                        const v = parseInt((e.target as HTMLInputElement).value);
                                        handleQuantityChange(item.id, isNaN(v) ? 0 : v);
                                    }}
                                    class="input input-xs input-bordered w-24 text-right font-mono tabular-nums"
                                />
                            </td>
                        </tr>
                    {/each}
                    {#if filtered.length === 0}
                        <tr>
                            <td colspan="4" class="text-center py-8 opacity-40 text-sm font-mono">No items match filters</td>
                        </tr>
                    {/if}
                </tbody>
            </table>
        </div>
        <div class="text-center text-[10px] opacity-20 font-bold uppercase pb-4">
            {filtered.length} / {allItems.length} items
        </div>
    {/if}
</div>
