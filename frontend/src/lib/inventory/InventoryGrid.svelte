<script lang="ts">
	import type { BagRead } from '$lib/core/types';
	import InventoryTile from './InventoryTile.svelte';

	let { bag }: { bag: BagRead } = $props();
</script>

<div class="grid w-fit grid-cols-10 gap-[3px]">
	{#each bag.slots as slot (`${bag.character}:${slot.slot}`)}
		<InventoryTile {slot} />
	{/each}
</div>
