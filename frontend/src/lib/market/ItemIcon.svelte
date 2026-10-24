<script lang="ts">
	// A grade-framed item icon like the /items tiles, with an optional stack count.
	import { iconUrl } from '$lib/inventory/api';
	import { gradeColor, gradeFrame } from '$lib/inventory/grades';
	import { formatCount } from '$lib/inventory/grid';

	let {
		itemType,
		grade,
		size = 34,
		count = null
	}: { itemType: number | null; grade: number | null; size?: number; count?: number | null } = $props();

	let iconFailed = $state(false);
</script>

<span
	class="relative inline-block shrink-0 border-2 ring-1 ring-black/60"
	style="width:{size}px;height:{size}px;background:{gradeColor(grade)};border-image:{gradeFrame(grade)} 1"
>
	{#if itemType != null && !iconFailed}
		<img src={iconUrl(itemType)} alt="" class="size-full" onerror={() => (iconFailed = true)} />
	{/if}
	{#if count != null && count > 1}
		<span class="absolute bottom-0 right-0.5 text-[10px] font-bold leading-tight text-white [text-shadow:0_0_2px_#000,0_0_2px_#000]">
			{formatCount(count)}
		</span>
	{/if}
</span>
