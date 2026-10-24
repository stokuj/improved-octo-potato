<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { formatCurrency } from '$lib/core/currency';
	import type { ListingsRead, MarketDayRead, MarketItemRead } from '$lib/core/types';
	import { gradeName } from '$lib/inventory/grades';
	import { fetchDays, fetchItems, fetchListings } from '$lib/market/api';
	import { formatVolume } from '$lib/market/chart';
	import { buildTree, gradeSiblings, OFFER_SORTS, tileStats, type OfferSort } from '$lib/market/tree';
	import CategoryTree from '$lib/market/CategoryTree.svelte';
	import ItemIcon from '$lib/market/ItemIcon.svelte';
	import MarketChart from '$lib/market/MarketChart.svelte';
	import OffersTable from '$lib/market/OffersTable.svelte';

	let items: MarketItemRead[] = $state([]);
	let days: MarketDayRead[] = $state([]);
	let listings: ListingsRead | null = $state(null);
	let loaded = $state(false);
	let loadingItem = $state(false);
	let error: string | null = $state(null);
	let query = $state('');
	let sort: OfferSort = $state('unit-asc');
	let range: 7 | 14 = $state(14);
	let seq = 0;

	const selectedId = $derived(Number(page.url.searchParams.get('item')) || items[0]?.id || null);
	const selected = $derived(items.find((i) => i.id === selectedId) ?? null);
	const tree = $derived(buildTree(items, query));
	const siblings = $derived(selected ? gradeSiblings(items, selected) : []);
	const stats = $derived(tileStats(days));
	const chartDays = $derived(days.slice(-range));

	onMount(async () => {
		try {
			items = await fetchItems();
		} catch {
			error = 'Could not load market data.';
		} finally {
			loaded = true;
		}
	});

	$effect(() => {
		if (selectedId != null) loadItem(selectedId);
	});

	async function loadItem(id: number) {
		const mine = ++seq; // ignore responses for an item the user already left
		loadingItem = true;
		error = null;
		[days, listings] = [[], null]; // never show the previous item's data under this heading
		try {
			const [d, l] = await Promise.all([fetchDays(id), fetchListings(id)]);
			if (mine !== seq) return;
			[days, listings] = [d, l];
		} catch {
			if (mine === seq) error = 'Could not load this item.';
		} finally {
			if (mine === seq) loadingItem = false;
		}
	}

	function select(id: number) {
		goto(`?item=${id}`, { replaceState: true, keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>Market · AA Tracker</title></svelte:head>

<div class="space-y-4">
	<div data-testid="market-header" class="flex flex-wrap items-center gap-x-6 gap-y-3">
		<h1 class="text-2xl font-black tracking-tight">Market</h1>
		{#if selected}
			<div class="flex items-center gap-3">
				<ItemIcon itemType={selected.item_type} grade={selected.item_grade} size={40} />
				<div>
					<div class="text-base font-bold">{selected.name}</div>
					<div class="text-xs opacity-60">{gradeName(selected.item_grade)} · {selected.category ?? 'Other'}</div>
				</div>
			</div>
			<div class="stats stats-horizontal ml-auto border border-base-200 bg-base-100">
				<div class="stat px-4 py-2">
					<div class="stat-title text-xs">Cheapest real offer</div>
					<div class="stat-value text-lg tabular-nums">{formatCurrency(selected.cheapest_real)}</div>
				</div>
				<div class="stat px-4 py-2">
					<div class="stat-title text-xs">Avg today</div>
					<div class="stat-value text-lg tabular-nums">{formatCurrency(stats.avgToday)}</div>
				</div>
				<div class="stat px-4 py-2">
					<div class="stat-title text-xs">Sold today / avg</div>
					<div class="stat-value text-lg tabular-nums">
						{formatVolume(stats.soldToday)} <span class="text-sm font-normal opacity-60">/ {formatVolume(stats.avgVolume)}</span>
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if error}
		<div role="alert" class="alert alert-error"><span>{error}</span></div>
	{/if}

	{#if loaded && !items.length && !error}
		<p class="opacity-60">No data yet. Import ArcheMarket CSV files on the Import page.</p>
	{:else if items.length}
		<div class="grid grid-cols-1 items-center gap-3 md:grid-cols-3">
			<label class="flex items-center gap-2 text-sm">
				<span class="opacity-60">Grade</span>
				<select
					class="select select-sm w-40"
					value={selectedId}
					disabled={siblings.length <= 1}
					onchange={(e) => select(Number(e.currentTarget.value))}
				>
					{#each siblings as s (s.id)}
						<option value={s.id}>{gradeName(s.item_grade)}</option>
					{/each}
				</select>
			</label>
			<input
				class="input input-sm w-full justify-self-center md:max-w-md"
				type="search"
				placeholder="Search items…"
				bind:value={query}
			/>
			<label class="flex items-center gap-2 text-sm md:justify-self-end">
				<span class="opacity-60">Sort</span>
				<select class="select select-sm w-40" bind:value={sort}>
					{#each OFFER_SORTS as o (o.value)}
						<option value={o.value}>{o.label}</option>
					{/each}
				</select>
			</label>
		</div>

		<div class="grid grid-cols-1 items-start gap-4 lg:grid-cols-[260px_1fr] min-[2300px]:grid-cols-[280px_1fr]">
			<aside class="card border border-base-200 bg-base-100">
				<div class="card-body p-2">
					<CategoryTree {tree} {selectedId} onSelect={select} />
				</div>
			</aside>

			{#if selected}
				<div class="grid min-w-0 grid-cols-1 items-start gap-4 min-[1700px]:grid-cols-[1fr_1.1fr] min-[2300px]:grid-cols-[1fr_1.4fr]">
					<section class="card min-w-0 border border-base-200 bg-base-100">
						<div class="card-body p-4">
							<h2 class="font-bold">Offers now</h2>
							{#if listings}
								<OffersTable data={listings} item={selected} {sort} />
							{/if}
						</div>
					</section>

					<section class="card min-w-0 border border-base-200 bg-base-100">
						<div class="card-body p-4">
							<div class="flex items-center gap-2">
								<h2 class="font-bold">Prices</h2>
								<span class="text-sm opacity-70">‹{gradeName(selected.item_grade)}› {selected.name}</span>
								<div class="join ml-auto">
									{#each [7, 14] as const as n (n)}
										<button
											type="button"
											class="btn join-item btn-xs {range === n ? 'btn-primary' : ''}"
											aria-pressed={range === n}
											onclick={() => (range = n)}>{n} days</button
										>
									{/each}
								</div>
							</div>
							{#if days.length}
								<MarketChart days={chartDays} />
							{:else if !loadingItem}
								<p class="py-8 text-center text-sm opacity-50">No market data for this item.</p>
							{/if}
						</div>
					</section>
				</div>
			{/if}
		</div>
	{/if}
</div>
