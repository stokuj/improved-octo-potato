<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import type { ListingRead, MarketDayRead, MarketItemRead, SummaryRow } from '$lib/core/types';
	import { fetchDays, fetchItems, fetchListings, fetchSummary } from '$lib/market/api';
	import MarketChart from '$lib/market/MarketChart.svelte';
	import ListingsTable from '$lib/market/ListingsTable.svelte';
	import SummaryTable from '$lib/market/SummaryTable.svelte';

	let items: MarketItemRead[] = $state([]);
	let summary: SummaryRow[] = $state([]);
	let days: MarketDayRead[] = $state([]);
	let listings: ListingRead[] = $state([]);
	let loaded = $state(false);
	let loadingItem = $state(false);
	let error: string | null = $state(null);
	let seq = 0;

	const selectedId = $derived(Number(page.url.searchParams.get('item')) || items[0]?.id || null);
	const selected = $derived(items.find((i) => i.id === selectedId) ?? null);

	onMount(async () => {
		try {
			[items, summary] = await Promise.all([fetchItems(), fetchSummary()]);
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
	<div class="flex flex-wrap items-center gap-3">
		<h1 class="text-2xl font-black tracking-tight mr-auto">Market</h1>
		{#if items.length}
			<label class="flex items-center gap-2 text-sm">
				<span class="opacity-60">Item</span>
				<select
					class="select select-bordered select-sm min-w-56"
					value={selectedId}
					onchange={(e) => select(Number(e.currentTarget.value))}
				>
					{#each items as i (i.id)}
						<option value={i.id}>{i.name}</option>
					{/each}
				</select>
			</label>
		{/if}
	</div>

	{#if error}
		<div role="alert" class="alert alert-error"><span>{error}</span></div>
	{/if}

	{#if loaded && !items.length && !error}
		<p class="opacity-60">No data yet. Import ArcheMarket CSV files on the Import page.</p>
	{:else if selected}
		<section class="card bg-base-100 border border-base-200">
			<div class="card-body p-4">
				<h2 class="font-bold">{selected.name} — last 14 days</h2>
				{#if days.length}
					<MarketChart {days} />
				{:else if !loadingItem}
					<p class="text-sm opacity-50 py-8 text-center">No market data for this item.</p>
				{/if}
			</div>
		</section>

		<section class="card bg-base-100 border border-base-200">
			<div class="card-body p-4">
				<h2 class="font-bold">Cheapest offers now</h2>
				<ListingsTable {listings} />
			</div>
		</section>
	{/if}

	{#if summary.length}
		<section class="card bg-base-100 border border-base-200">
			<div class="card-body p-4">
				<h2 class="font-bold">Today vs last 7 days</h2>
				<SummaryTable rows={summary} {selectedId} onSelect={select} />
			</div>
		</section>
	{/if}
</div>
