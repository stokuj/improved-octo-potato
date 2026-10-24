<script lang="ts">
	// The selected item's offers from its newest scan, with bait-sized stacks marked.
	import { formatCurrency } from '$lib/core/currency';
	import type { ListingsRead, MarketItemRead } from '$lib/core/types';
	import ItemIcon from './ItemIcon.svelte';
	import { sortOffers, type OfferSort } from './tree';

	let { data, item, sort }: { data: ListingsRead; item: MarketItemRead; sort: OfferSort } = $props();

	const STATUS_WORDS: Record<string, string> = {
		no_buyout: 'no buyout',
		not_on_page1: 'not on page 1',
		no_result: 'no result',
		error: 'error'
	};

	const offers = $derived(sortOffers(data.listings, sort));
	const statuses = $derived(
		data.listings.filter((l) => l.status !== 'ok').map((l) => STATUS_WORDS[l.status] ?? l.status)
	);
	const scanTime = $derived(data.captured_at ? new Date(data.captured_at + 'Z').toLocaleString('en-GB') : null);
</script>

{#if data.listings.length === 0}
	<p class="text-sm opacity-50">No listings imported for this item yet.</p>
{:else}
	<p class="text-xs opacity-60 mb-2">Scan {scanTime} · page 1 (top {offers.length})</p>
	{#each statuses as s}
		<span class="badge badge-ghost badge-sm mr-1">{s}</span>
	{/each}
	{#if offers.length}
		<table class="table table-sm">
			<thead>
				<tr>
					<th>Name</th>
					<th class="text-right">Stack</th>
					<th class="text-right">Unit price</th>
					<th class="text-right">Listing price</th>
				</tr>
			</thead>
			<tbody>
				{#each offers as l (l.rank)}
					<tr>
						<td>
							<div class="flex items-center gap-2">
								<ItemIcon itemType={item.item_type} grade={item.item_grade} count={l.stack} />
								<span class="whitespace-nowrap">{item.name}</span>
								{#if l.tiny}
									<span class="badge badge-warning badge-sm whitespace-nowrap" title="Smaller than a useful amount: likely bait">tiny stack</span>
								{/if}
							</div>
						</td>
						<td class="text-right tabular-nums">{l.stack?.toLocaleString('en-US')}</td>
						<td class="text-right tabular-nums">{formatCurrency(l.unit_price)}</td>
						<td class="text-right tabular-nums">{formatCurrency(l.listing_price)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
{/if}
