<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { user } from '$lib/auth.svelte.js';
    import { API_BASE_URL } from '$lib/config.js';

    let {
        apiEndpoint = '/items/',
        requireAuth = false,
        showOnlySaved = false
    } = $props();

    /** @typedef {{ id: number, name: string, category: string, grade: string, current_price: number | null, updated_at: string }} ItemRow */

    /** @type {ItemRow[]} */
    let items = $state([]);
    let total = $state(0);
    let offset = $state(0);
    let limit = 100;
    let loading = $state(false);
    let hasMore = $state(true);
    /** @type {string | null} */
    let fetchError = $state(null);
    /** @type {Set<number>} */
    let savingIds = $state(new Set());
    /** @type {Set<number>} */
    let savedIds = $state(new Set());

    let searchQuery = $state('');
    let selectedCategory = $state('');
    let selectedGrade = $state('');

    const CATEGORIES = [
        'Special Product', 'Weapons', 'Armor', 'Accessories', 'Instrument',
        'Costume', 'Consumables', 'Crafting', 'Machining', 'Companions',
        'Other', 'Lunagem', 'Lunastone'
    ];

    const GRADES = [
        'All', 'Grand', 'Rare', 'Arcane', 'Heroic', 'Unique',
        'Celestial', 'Divine', 'Epic', 'Legendary', 'Mythic', 'Eternal'
    ];

    const ROW_HEIGHT = 72;
    const VISIBLE_COUNT = 20;
    let scrollY = $state(0);
    let containerTop = $state(0);
    /** @type {HTMLDivElement | undefined} */
    let containerRef;

    let startIndex = $derived(Math.max(0, Math.floor((scrollY - containerTop) / ROW_HEIGHT)));
    let endIndex = $derived(Math.min(items.length, startIndex + VISIBLE_COUNT));
    let visibleItems = $derived(items.slice(startIndex, endIndex));
    let paddingTop = $derived(startIndex * ROW_HEIGHT);
    let paddingBottom = $derived(Math.max(0, (items.length - endIndex) * ROW_HEIGHT));

    async function loadSavedIds() {
        if (!user.isLoggedIn) {
            savedIds = new Set();
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/user-items/ids`, {
                credentials: 'include'
            });
            if (!response.ok) return;
            const ids = await response.json();
            savedIds = new Set(ids);
        } catch (e) {
            console.error('Error loading saved IDs:', e);
        }
    }

    async function loadItems(reset = false) {
        if (loading) return;
        if (!reset && !hasMore) return;

        loading = true;
        if (reset) {
            offset = 0;
            items = [];
            hasMore = true;
        }

        const params = new URLSearchParams({
            offset: offset.toString(),
            limit: limit.toString()
        });

        if (searchQuery) params.append('q', searchQuery);
        if (selectedCategory) params.append('category', selectedCategory);
        if (selectedGrade && selectedGrade !== 'All') params.append('grade', selectedGrade);

        try {
            fetchError = null;
            const response = await fetch(`${API_BASE_URL}${apiEndpoint}?${params.toString()}`, {
                credentials: 'include'
            });

            if (response.status === 401 && requireAuth) {
                goto('/auth');
                return;
            }

            if (response.ok) {
                const data = await response.json();
                /** @type {ItemRow[]} */
                const nextItems = data.items;
                items = [...items, ...nextItems];
                total = data.total;
                offset += limit;
                hasMore = items.length < total;
            } else {
                fetchError = `Server error: ${response.status}`;
            }
        } catch (e) {
            console.error('Error loading items:', e);
            fetchError = 'Network error: Connection failed';
        } finally {
            loading = false;
        }
    }

    /** @param {number} itemId */
    async function toggleSaved(itemId) {
        if (!user.isLoggedIn) {
            goto('/auth');
            return;
        }
        if (savingIds.has(itemId)) return;

        savingIds = new Set(savingIds).add(itemId);
        const alreadySaved = savedIds.has(itemId);

        try {
            const response = await fetch(`${API_BASE_URL}/user-items/${itemId}`, {
                method: alreadySaved ? 'DELETE' : 'POST',
                credentials: 'include'
            });

            if (!response.ok && response.status !== 204 && response.status !== 201) {
                fetchError = `Save failed: ${response.status}`;
                return;
            }

            const nextSaved = new Set(savedIds);
            if (alreadySaved) {
                nextSaved.delete(itemId);
            } else {
                nextSaved.add(itemId);
            }
            savedIds = nextSaved;

            if (showOnlySaved) {
                await loadItems(true);
            }
        } catch (e) {
            console.error('Error toggling saved item:', e);
            fetchError = 'Network error: Unable to save item';
        } finally {
            const nextSaving = new Set(savingIds);
            nextSaving.delete(itemId);
            savingIds = nextSaving;
        }
    }

    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let searchTimeout;
    function handleSearch() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadItems(true), 300);
    }

    const updateContainerPos = () => {
        if (!containerRef) return;
        const rect = containerRef.getBoundingClientRect();
        containerTop = rect.top + window.scrollY;
    };

    onMount(() => {
        const init = async () => {
            if (requireAuth && !user.loading && !user.isLoggedIn) {
                goto('/auth');
                return;
            }

            await loadSavedIds();
            await loadItems(true);
            updateContainerPos();
        };

        init();

        window.addEventListener('scroll', updateContainerPos, { passive: true });
        window.addEventListener('resize', updateContainerPos);

        return () => {
            window.removeEventListener('scroll', updateContainerPos);
            window.removeEventListener('resize', updateContainerPos);
        };
    });

    $effect(() => {
        if (user.loading) return;
        if (!user.isLoggedIn) {
            savedIds = new Set();
            return;
        }
        loadSavedIds();
    });

    $effect(() => {
        if (items.length > 0) {
            updateContainerPos();
        }
        if (hasMore && !loading && endIndex > items.length - 20) {
            loadItems();
        }
    });

    /** @param {string} grade */
    function getGradeBadgeClass(grade) {
        void grade;
        return 'badge-outline opacity-50 font-medium border-base-content/20';
    }

    /** @param {string} dateStr */
    function formatTime(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /** @param {number | null | undefined} totalBronze */
    function splitCurrency(totalBronze) {
        if (!totalBronze && totalBronze !== 0) return null;
        const gold = Math.floor(totalBronze / 10000);
        const silver = Math.floor((totalBronze % 10000) / 100);
        const bronze = totalBronze % 100;
        return { gold, silver, bronze };
    }
</script>

<svelte:window bind:scrollY />

<div class="space-y-6">
    <div class="flex flex-col md:flex-row gap-4 items-center justify-between bg-base-100 p-4 rounded-box shadow-sm border border-base-200 sticky top-0 z-20">
        <div class="join w-full md:w-auto">
            <input
                class="input input-bordered join-item w-full md:w-64 focus:outline-none focus:border-primary"
                placeholder="Search items..."
                bind:value={searchQuery}
                oninput={handleSearch}
            />
            <button class="btn join-item btn-primary" aria-label="Search">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </button>
        </div>

        <div class="flex gap-2 w-full md:w-auto">
            <select class="select select-bordered select-sm md:select-md flex-1" bind:value={selectedCategory} onchange={() => loadItems(true)}>
                <option value="">All Categories</option>
                {#each CATEGORIES as cat}
                    <option value={cat}>{cat}</option>
                {/each}
            </select>

            <select class="select select-bordered select-sm md:select-md flex-1" bind:value={selectedGrade} onchange={() => loadItems(true)}>
                <option value="All">All Grades</option>
                {#each GRADES.filter((g) => g !== 'All') as g}
                    <option value={g}>{g}</option>
                {/each}
            </select>
        </div>
    </div>

    {#if fetchError}
        <div class="alert alert-error shadow-lg">
            <span>{fetchError}</span>
            <button class="btn btn-sm btn-ghost underline" onclick={() => loadItems(true)}>Retry</button>
        </div>
    {/if}

    <div class="bg-base-100 rounded-box shadow-lg border border-base-200" bind:this={containerRef}>
        <div class="grid grid-cols-12 gap-4 p-4 bg-base-200/50 text-xs font-black uppercase tracking-widest opacity-60 rounded-t-box border-b border-base-200">
            <div class="col-span-5 md:col-span-4">Item Name</div>
            <div class="hidden md:block col-span-3">Category</div>
            <div class="col-span-3 md:col-span-2 text-center">Grade</div>
            <div class="col-span-4 md:col-span-2 text-right">Price</div>
            <div class="hidden md:block col-span-1 text-center">Save</div>
        </div>

        <div style="padding-top: {paddingTop}px; padding-bottom: {paddingBottom}px;">
            {#each visibleItems as item (item.id)}
                {@const c = splitCurrency(item.current_price)}
                {@const isSaved = savedIds.has(item.id)}
                {@const isSaving = savingIds.has(item.id)}
                <div class="grid grid-cols-12 gap-4 px-4 items-center border-b border-base-100 hover:bg-primary/5 transition-colors group" style="height: {ROW_HEIGHT}px;">
                    <div class="col-span-5 md:col-span-4 flex flex-col min-w-0">
                        <a href={`/items/${item.id}`} class="font-bold text-base truncate group-hover:text-primary hover:text-primary hover:underline transition-colors">
                            {item.name}
                        </a>
                        <span class="text-[10px] opacity-40 uppercase font-black">Updated: {formatTime(item.updated_at)}</span>
                    </div>

                    <div class="hidden md:block col-span-3">
                        <span class="badge badge-ghost badge-sm text-[10px] font-bold opacity-60 uppercase truncate max-w-full">{item.category}</span>
                    </div>

                    <div class="col-span-3 md:col-span-2 text-center">
                        <span class="badge {getGradeBadgeClass(item.grade)} badge-sm py-2 px-3 uppercase text-[10px]">{item.grade}</span>
                    </div>

                    <div class="col-span-4 md:col-span-2 text-right tabular-nums">
                        {#if c}
                            <div class="flex items-center justify-end gap-1 font-black">
                                {#if c.gold > 0}
                                    <span>{c.gold}<span class="text-yellow-500 ml-0.5 uppercase text-[10px]">g</span></span>
                                {/if}
                                {#if c.silver > 0 || c.gold > 0}
                                    <span>{c.silver.toString().padStart(2, '0')}<span class="text-slate-400 ml-0.5 uppercase text-[10px]">s</span></span>
                                {/if}
                                <span>{c.bronze.toString().padStart(2, '0')}<span class="text-orange-700 ml-0.5 uppercase text-[10px]">b</span></span>
                            </div>
                        {:else}
                            <span class="opacity-20 italic text-sm">--</span>
                        {/if}
                    </div>

                    <div class="hidden md:block col-span-1 text-center">
                        <button
                            class="btn btn-ghost btn-circle btn-sm hover:scale-110 active:scale-95 transition-all {isSaved ? 'text-primary' : 'text-base-content/20 hover:text-primary'}"
                            aria-label="Save item"
                            disabled={isSaving}
                            onclick={() => toggleSaved(item.id)}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill={isSaved ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.921-.755 1.688-1.54 1.118l-3.976-2.888a1 1 0 00-1.175 0l-3.976 2.888c-.784.57-1.838-.197-1.539-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>
                        </button>
                    </div>
                </div>
            {/each}
        </div>

        {#if loading}
            <div class="flex justify-center p-8 bg-base-100 border-t border-base-200">
                <span class="loading loading-dots loading-lg text-primary"></span>
            </div>
        {/if}

        {#if items.length === 0 && !loading}
            <div class="p-20 text-center opacity-30 italic">No items found matching your criteria.</div>
        {/if}
    </div>

    <div class="text-center text-[10px] opacity-20 font-bold uppercase pb-10">
        Total Items: {total} • Loaded: {items.length} • Showing: {visibleItems.length}
    </div>
</div>

<style>
    .sticky {
        backdrop-filter: blur(12px);
        background-color: oklch(var(--b1) / 0.8);
    }
</style>
