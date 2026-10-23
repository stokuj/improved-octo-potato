<script lang="ts">
	import type { SlotRead } from '$lib/core/types';
	import InventoryTile from './InventoryTile.svelte';

	let { slots }: { slots: SlotRead[] } = $props();
</script>

<!-- Fluid: tiles shrink with the panel; max-w-96 keeps a lone grid at about the old 36px tiles. -->
<div class="grid w-full max-w-96 grid-cols-10 gap-[2px]">
	{#each slots as slot (slot.slot)}
		<InventoryTile {slot} />
	{/each}
</div>
