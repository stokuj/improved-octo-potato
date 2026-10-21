<script lang="ts">
	import { formatCurrency } from '$lib/core/currency';
	import type { SummaryRow } from '$lib/core/types';
	import { formatVolume } from './chart';

	let {
		rows,
		selectedId,
		onSelect
	}: { rows: SummaryRow[]; selectedId: number | null; onSelect: (id: number) => void } = $props();

	type Key = 'name' | 'today_avg' | 'avg_7d' | 'change_pct' | 'sold_today' | 'avg_daily_volume';
	const COLUMNS: { key: Key; label: string }[] = [
		{ key: 'name', label: 'Item' },
		{ key: 'today_avg', label: 'Avg today' },
		{ key: 'avg_7d', label: 'Avg 7d' },
		{ key: 'change_pct', label: 'Change' },
		{ key: 'sold_today', label: 'Sold today' },
		{ key: 'avg_daily_volume', label: 'Avg / day' }
	];

	let sortKey: Key = $state('name');
	let sortDir: 'asc' | 'desc' = $state('asc');

	function sortBy(key: Key) {
		if (key === sortKey) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		else [sortKey, sortDir] = [key, key === 'name' ? 'asc' : 'desc'];
	}

	const sorted = $derived(
		[...rows].sort((a, b) => {
			const x = a[sortKey];
			const y = b[sortKey];
			if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1; // nulls last
			const c = typeof x === 'string' ? x.localeCompare(y as string) : (x as number) - (y as number);
			return sortDir === 'asc' ? c : -c;
		})
	);

	function pct(v: number | null): string {
		return v == null ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;
	}
</script>

<div class="overflow-x-auto">
	<table class="table table-sm">
		<thead>
			<tr>
				{#each COLUMNS as c}
					<th class={c.key === 'name' ? '' : 'text-right'} aria-sort={sortKey === c.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
						<button class="font-bold" onclick={() => sortBy(c.key)}>
							{c.label}{sortKey === c.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
						</button>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sorted as r (r.item_id)}
				<tr class="cursor-pointer hover {r.item_id === selectedId ? 'bg-base-200' : ''}" onclick={() => onSelect(r.item_id)}>
					<td>{r.name}</td>
					<td class="text-right tabular-nums">{formatCurrency(r.today_avg)}</td>
					<td class="text-right tabular-nums">{formatCurrency(r.avg_7d)}</td>
					<td class="text-right tabular-nums {r.change_pct == null ? '' : r.change_pct >= 0 ? 'text-success' : 'text-error'}">{pct(r.change_pct)}</td>
					<td class="text-right tabular-nums">{formatVolume(r.sold_today)}</td>
					<td class="text-right tabular-nums">{formatVolume(r.avg_daily_volume)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
