<script lang="ts">
	import type { SlotRead } from '$lib/core/types';
	import InventoryTile from './InventoryTile.svelte';

	let { slots }: { slots: SlotRead[] } = $props();
</script>

<div class="grid w-fit grid-cols-10 gap-[3px]">
	{#each slots as slot (slot.slot)}
		<InventoryTile {slot} />
	{/each}
</div>
