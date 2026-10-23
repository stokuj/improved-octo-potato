<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import type { BagRead, CharacterRead } from '$lib/core/types';
	import { fetchBag, fetchCharacters } from '$lib/inventory/api';
	import InventoryGrid from '$lib/inventory/InventoryGrid.svelte';
	import { ApiError } from '$lib/market/api';

	let characters: CharacterRead[] = $state([]);
	let bag: BagRead | null = $state(null);
	let loaded = $state(false);
	let error: string | null = $state(null);
	let seq = 0;

	// An unknown ?character= (renamed character, stale bookmark) falls back to the first tab.
	const requested = $derived(page.url.searchParams.get('character'));
	const selected = $derived(
		characters.find((c) => c.character === requested)?.character ?? characters[0]?.character ?? null
	);

	const when = (x: string | null | undefined) => (x ? new Date(x + 'Z').toLocaleString('en-GB') : '—');

	onMount(async () => {
		try {
			characters = await fetchCharacters();
		} catch (e) {
			error = e instanceof ApiError && e.status === 401 ? 'Sign in to see your inventory.' : 'Could not load your inventory.';
		} finally {
			loaded = true;
		}
	});

	$effect(() => {
		if (selected != null && characters.length) loadBag(selected);
	});

	async function loadBag(character: string) {
		const mine = ++seq; // ignore responses for a character the user already left
		bag = null;
		try {
			const b = await fetchBag(character);
			if (mine === seq) bag = b;
		} catch {
			if (mine === seq) error = 'Could not load this bag.';
		}
	}

	function select(character: string) {
		goto(`?character=${encodeURIComponent(character)}`, { replaceState: true, keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>Inventory · AA Tracker</title></svelte:head>

<div class="space-y-4">
	<h1 class="text-2xl font-black tracking-tight">Inventory</h1>

	{#if error}
		<div role="alert" class="alert alert-error text-sm">{error}</div>
	{:else if loaded && !characters.length}
		<p class="opacity-70">
			No inventory yet. Click <b>Bag</b> in game (ArcheBag addon), then upload <code>inventory.csv</code> on
			<a href="/import" class="link link-primary">Import</a>.
		</p>
	{:else if characters.length}
		<div class="flex flex-wrap items-center gap-3">
			<div role="tablist" class="tabs tabs-box">
				{#each characters as c (c.character)}
					<button
						role="tab"
						class="tab {c.character === selected ? 'tab-active' : ''}"
						aria-selected={c.character === selected}
						onclick={() => select(c.character)}
					>
						{c.character} · {c.slot_count}
					</button>
				{/each}
			</div>
			{#if bag}
				<span class="text-xs opacity-60">
					snapshot {when(bag.captured_at)} · previous {when(bag.previous_captured_at)}
				</span>
			{/if}
		</div>

		{#if bag}
			<InventoryGrid {bag} />
		{:else}
			<span class="loading loading-spinner loading-md"></span>
		{/if}
	{/if}
</div>
