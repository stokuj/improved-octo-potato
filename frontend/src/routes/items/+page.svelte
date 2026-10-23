<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import type { CharacterRead, ChestRead } from '$lib/core/types';
	import { fetchCharacters, fetchChests } from '$lib/inventory/api';
	import GridPanel from '$lib/inventory/GridPanel.svelte';
	import { ALL, chestLabel, pickTab } from '$lib/inventory/grid';
	import { ApiError } from '$lib/market/api';

	let characters: CharacterRead[] = $state([]);
	let chests: ChestRead[] = $state([]);
	let loaded = $state(false);
	let error: string | null = $state(null);

	// Unknown values (renamed character, stale bookmark) fall back to All.
	const character = $derived(
		pickTab(
			page.url.searchParams.get('character'),
			characters.map((c) => c.character)
		)
	);
	const chest = $derived(
		pickTab(
			page.url.searchParams.get('chest'),
			chests.map((c) => String(c.chest))
		)
	);
	const shownCharacters = $derived(character === ALL ? characters : characters.filter((c) => c.character === character));
	const shownChests = $derived(chest === ALL ? chests : chests.filter((c) => String(c.chest) === chest));

	onMount(async () => {
		try {
			[characters, chests] = await Promise.all([fetchCharacters(), fetchChests()]);
		} catch (e) {
			error = e instanceof ApiError && e.status === 401 ? 'Sign in to see your items.' : 'Could not load your items.';
		} finally {
			loaded = true;
		}
	});

	function select(param: 'character' | 'chest', value: string) {
		const q = new URLSearchParams(page.url.searchParams);
		if (value === ALL) q.delete(param);
		else q.set(param, value);
		goto(q.size ? `?${q}` : page.url.pathname, { replaceState: true, keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>Items · AA Tracker</title></svelte:head>

{#snippet tabs(param: 'character' | 'chest', selected: string, options: { value: string; label: string }[])}
	<div role="tablist" class="tabs tabs-box w-fit">
		{#each [{ value: ALL, label: 'All' }, ...options] as o (o.value)}
			<button
				role="tab"
				class="tab {o.value === selected ? 'tab-active' : ''}"
				aria-selected={o.value === selected}
				onclick={() => select(param, o.value)}
			>
				{o.label}
			</button>
		{/each}
	</div>
{/snippet}

<div class="space-y-4">
	<h1 class="text-2xl font-black tracking-tight">Items</h1>

	{#if error}
		<div role="alert" class="alert alert-error text-sm">{error}</div>
	{:else if loaded}
		<!-- From xl (1280px): two equal halves, two grids per row each (20 columns a side); narrower stacks. -->
		<div class="flex flex-col gap-6 xl:flex-row xl:items-start">
			<section aria-label="Characters" class="min-w-0 space-y-4 xl:flex-1 xl:basis-0">
				<h2 class="text-xs font-semibold uppercase tracking-wide opacity-60">Characters</h2>
				{#if characters.length}
					{@render tabs(
						'character',
						character,
						characters.map((c) => ({ value: c.character, label: c.character }))
					)}
					{#each shownCharacters as c (c.character)}
						<div class="space-y-2">
							{#if character === ALL}<h3 class="font-bold">{c.character}</h3>{/if}
							<div class="grid items-start gap-3 sm:grid-cols-2">
								{#if c.bag}<GridPanel title="Bag" grid={c.bag} />{/if}
								{#if c.bank}<GridPanel title="Warehouse" grid={c.bank} />{/if}
							</div>
						</div>
					{/each}
				{:else}
					<p class="text-sm opacity-70">
						No characters yet. Click <b>Bag</b> in game (ArcheBag), then upload <code>inventory.csv</code> on
						<a href="/import" class="link link-primary">Import</a>.
					</p>
				{/if}
			</section>

			<section
				aria-label="House chests"
				class="min-w-0 space-y-4 xl:flex-1 xl:basis-0 xl:border-l xl:border-base-content/10 xl:pl-6"
			>
				<h2 class="text-xs font-semibold uppercase tracking-wide opacity-60">House chests</h2>
				{#if chests.length}
					{@render tabs(
						'chest',
						chest,
						chests.map((c) => ({ value: String(c.chest), label: chestLabel(c) }))
					)}
					<div class="grid items-start gap-3 sm:grid-cols-2">
						{#each shownChests as c (c.chest)}
							<GridPanel title={chestLabel(c)} grid={c} detail="saved by {c.saved_by}" />
						{/each}
					</div>
				{:else}
					<p class="text-sm opacity-70">
						No chests yet. Click <b>Chest</b> in game, save an open chest, then upload <code>chests.csv</code> on
						<a href="/import" class="link link-primary">Import</a>.
					</p>
				{/if}
			</section>
		</div>
	{:else}
		<span class="loading loading-spinner loading-md"></span>
	{/if}
</div>
