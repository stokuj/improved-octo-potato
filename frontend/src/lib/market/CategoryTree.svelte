<script lang="ts">
	// The Auction House item tree: folding categories, one leaf per item type with its cheapest real price.
	import { nodePrice, shortPrice, type TreeCategory } from './tree';

	let {
		tree,
		selectedId,
		onSelect
	}: { tree: TreeCategory[]; selectedId: number | null; onSelect: (id: number) => void } = $props();

	let folded: Record<string, boolean> = $state({});
</script>

<nav class="text-sm" data-testid="category-tree">
	{#each tree as cat (cat.name)}
		<button
			type="button"
			class="flex w-full items-center gap-1 rounded px-2 py-1 text-left font-semibold hover:bg-base-200"
			aria-expanded={!folded[cat.name]}
			onclick={() => (folded[cat.name] = !folded[cat.name])}
		>
			<span class="w-3 opacity-60">{folded[cat.name] ? '▸' : '▾'}</span>{cat.name}
		</button>
		{#if !folded[cat.name]}
			{#each cat.nodes as node (node.key)}
				{@const current = node.items.some((i) => i.id === selectedId)}
				<button
					type="button"
					class="flex w-full items-center justify-between gap-2 rounded py-1 pl-6 pr-2 text-left hover:bg-base-200 {current
						? 'bg-primary/10 font-semibold text-primary'
						: ''}"
					aria-current={current ? 'true' : undefined}
					onclick={() => onSelect(node.items[0].id)}
				>
					<span class="truncate">{node.name}</span>
					<span class="whitespace-nowrap tabular-nums text-xs opacity-70">{shortPrice(nodePrice(node))}</span>
				</button>
			{/each}
		{/if}
	{:else}
		<p class="px-2 py-1 opacity-50">No items match</p>
	{/each}
</nav>
