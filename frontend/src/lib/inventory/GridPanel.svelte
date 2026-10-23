<script lang="ts">
	import type { GridRead } from '$lib/core/types';
	import InventoryGrid from './InventoryGrid.svelte';
	import { snapshotTime } from './grid';

	let { title, grid, detail }: { title: string; grid: GridRead; detail?: string } = $props();
</script>

<div data-testid="grid-panel" class="space-y-1">
	<h3 class="text-sm font-bold">
		{title}
		<span class="font-normal opacity-60">{grid.filled} / {grid.slot_count}{detail ? ` · ${detail}` : ''}</span>
	</h3>
	<p class="text-xs opacity-60">
		snapshot {snapshotTime(grid.captured_at)} · previous {snapshotTime(grid.previous_captured_at)}
	</p>
	<InventoryGrid slots={grid.slots} />
</div>
