<script lang="ts">
	import type { SlotRead } from '$lib/core/types';
	import { iconUrl } from './api';
	import { gradeColor } from './grades';
	import { changeDot, tileLabel } from './grid';

	let { slot }: { slot: SlotRead } = $props();

	let iconFailed = $state(false);
	const label = $derived(tileLabel(slot));
	const dot = $derived(changeDot(slot.change));
	const DOT = { up: 'bg-green-500', down: 'bg-red-500', new: 'bg-blue-500' } as const;
</script>

<!-- DaisyUI opens the tip on .tooltip:has(:focus-visible), so the focusable square sits inside it. -->
<div class="tooltip" data-tip={label}>
	<!-- Focusable so keyboard users can open the tooltip; the tile itself has no action. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		data-testid="tile"
		tabindex="0"
		role="img"
		aria-label={label}
		class="relative size-9 rounded-md focus:outline-2 focus:outline-primary {slot.item == null
			? 'border border-dashed border-base-content/20'
			: 'ring-1 ring-black/15'}"
		style={slot.item != null && (!slot.icon || iconFailed) ? `background:${gradeColor(slot.item_grade)}` : ''}
	>
		{#if slot.item != null && slot.icon && !iconFailed}
			<img src={iconUrl(slot.icon)} alt="" class="size-full rounded-md" onerror={() => (iconFailed = true)} />
		{/if}
		{#if slot.count > 1}
			<span class="absolute bottom-0 right-0.5 text-[10px] font-bold leading-tight text-white [text-shadow:0_0_2px_#000,0_0_2px_#000]">
				{slot.count}
			</span>
		{/if}
		{#if dot}
			<span class="absolute -left-1 -top-1 size-2.5 rounded-full border border-base-100 {DOT[dot]}"></span>
		{/if}
	</div>
</div>
