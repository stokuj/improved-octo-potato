<script lang="ts">
	import { getUserState } from '$lib/core/auth.svelte.js';
	import type { ImportFileResult } from '$lib/core/types';
	import ImportDropzone from '$lib/market/ImportDropzone.svelte';

	const user = getUserState();
	let results: ImportFileResult[] = $state([]);
</script>

<svelte:head><title>Import · AA Tracker</title></svelte:head>

<div class="space-y-4">
	<h1 class="text-2xl font-black tracking-tight">Import</h1>

	{#if !user.isLoggedIn}
		<p class="opacity-70">Sign in to import files.</p>
	{:else}
		<p class="text-sm opacity-70">
			Drop <code>inventory.csv</code> (ArcheBag), plus <code>market.csv</code> and
			<code>listings.csv</code> (ArcheMarket, admin only).
		</p>
		<ImportDropzone onResults={(r) => (results = r)} />

		{#if results.length}
			<div class="overflow-x-auto">
				<table class="table table-sm">
					<thead>
						<tr>
							<th>File</th><th>Kind</th><th class="text-right">Rows</th><th class="text-right">Inserted</th>
							<th class="text-right">Updated</th><th class="text-right">Skipped</th><th class="text-right">Errors</th>
						</tr>
					</thead>
					<tbody>
						{#each results as r}
							<tr data-testid="result-row">
								<td>{r.filename}</td>
								<td>{r.kind ?? '—'}</td>
								<td class="text-right tabular-nums">{r.rows}</td>
								<td class="text-right tabular-nums">{r.inserted}</td>
								<td class="text-right tabular-nums">{r.updated}</td>
								<td class="text-right tabular-nums">{r.skipped}</td>
								<td class="text-right tabular-nums {r.errors.length ? 'text-error' : ''}">{r.error_count}</td>
							</tr>
							{#if r.errors.length}
								<tr>
									<td colspan="7">
										<ul class="text-xs text-error space-y-0.5">
											{#each r.errors as e}
												<li>{e.line ? `line ${e.line}: ` : ''}{e.reason}</li>
											{/each}
											{#if r.error_count > r.errors.length}
												<li class="opacity-70">…and {r.error_count - r.errors.length} more</li>
											{/if}
										</ul>
									</td>
								</tr>
							{/if}
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>
