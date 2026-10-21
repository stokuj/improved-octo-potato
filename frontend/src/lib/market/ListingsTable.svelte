<script lang="ts">
	import { formatCurrency } from '$lib/core/currency';
	import type { ListingRead } from '$lib/core/types';

	let { listings }: { listings: ListingRead[] } = $props();

	const STATUS_WORDS: Record<string, string> = {
		no_buyout: 'no buyout',
		not_on_page1: 'not on page 1',
		no_result: 'no result',
		error: 'error'
	};

	const offers = $derived(listings.filter((l) => l.status === 'ok'));
	const statuses = $derived(listings.filter((l) => l.status !== 'ok').map((l) => STATUS_WORDS[l.status] ?? l.status));
	const scanTime = $derived(
		listings.length ? new Date(listings[0].captured_at + 'Z').toLocaleString('en-GB') : null
	);
</script>

{#if listings.length === 0}
	<p class="text-sm opacity-50">No listings imported for this item yet.</p>
{:else}
	<p class="text-xs opacity-50 mb-2">Scan {scanTime}</p>
	{#each statuses as s}
		<span class="badge badge-ghost badge-sm mr-1">{s}</span>
	{/each}
	{#if offers.length}
		<table class="table table-sm">
			<thead>
				<tr><th>#</th><th class="text-right">Unit price</th><th class="text-right">Stack</th><th class="text-right">Listing price</th></tr>
			</thead>
			<tbody>
				{#each offers as l (l.rank)}
					<tr>
						<td>{l.rank}</td>
						<td class="text-right tabular-nums">{formatCurrency(l.unit_price)}</td>
						<td class="text-right tabular-nums">{l.stack}</td>
						<td class="text-right tabular-nums">{formatCurrency(l.listing_price)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
{/if}
