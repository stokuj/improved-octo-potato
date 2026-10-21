<script lang="ts">
	import type { ImportFileResult } from '$lib/core/types';
	import { ApiError, uploadFiles } from './api';

	let { onResults }: { onResults: (r: ImportFileResult[]) => void } = $props();

	let uploading = $state(false);
	let dragging = $state(false);
	let error: string | null = $state(null);

	async function upload(list: FileList | File[] | null | undefined) {
		const files = [...(list ?? [])];
		if (!files.length || uploading) return;
		uploading = true;
		error = null;
		try {
			onResults(await uploadFiles(files));
		} catch (e) {
			error =
				e instanceof ApiError && e.status === 401
					? 'Session expired — sign in again.'
					: e instanceof ApiError && e.status === 429
						? 'Too many uploads — wait a minute and try again.'
						: 'Upload failed. Is the backend running?';
		} finally {
			uploading = false;
		}
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		upload(e.dataTransfer?.files);
	}
</script>

<div
	data-testid="dropzone"
	role="region"
	aria-label="CSV drop zone"
	class="border-2 border-dashed rounded-box p-10 text-center transition-colors {dragging ? 'border-primary bg-primary/5' : 'border-base-300'}"
	ondragover={(e) => {
		e.preventDefault();
		dragging = true;
	}}
	ondragleave={() => (dragging = false)}
	ondrop={onDrop}
>
	<p class="mb-4 opacity-70">Drop <code>market.csv</code> and <code>listings.csv</code> here, or</p>
	<label class="btn btn-primary btn-sm">
		{#if uploading}<span class="loading loading-spinner loading-xs"></span>{/if}
		Choose files
		<input
			type="file"
			class="hidden"
			multiple
			accept=".csv"
			disabled={uploading}
			onchange={(e) => {
				upload(e.currentTarget.files);
				e.currentTarget.value = '';
			}}
		/>
	</label>
	{#if error}
		<div role="alert" class="alert alert-error mt-4 text-sm"><span>{error}</span></div>
	{/if}
</div>
