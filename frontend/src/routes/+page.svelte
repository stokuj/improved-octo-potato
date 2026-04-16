<script>
	import { mockItems } from '$lib/mockData.js';
</script>

<div class="space-y-8">
	<!-- Hero section -->
	<section class="hero bg-base-200 rounded-box p-8 shadow-inner">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<h1 class="text-5xl font-extrabold text-primary">AA Tracker Svelte</h1>
				<p class="py-6 text-lg text-base-content/70">
					Witaj w prototypie nowego frontendu zbudowanego w Svelte 5, Tailwind v4 i daisyUI v5.
				</p>
				<button class="btn btn-primary btn-lg shadow-xl hover:scale-105 transition-transform">Zacznij tutaj</button>
			</div>
		</div>
	</section>

	<!-- Data Showcase -->
	<section class="card bg-base-100 shadow-sm border border-base-200">
		<div class="card-body">
			<h2 class="card-title text-2xl mb-4 text-secondary">Przykładowe dane przedmiotów</h2>
			<div class="overflow-x-auto">
				<table class="table table-zebra w-full shadow-md rounded-lg overflow-hidden border border-base-200">
					<thead class="bg-base-300">
						<tr>
							<th class="p-4">ID</th>
							<th class="p-4">Nazwa</th>
							<th class="p-4">Opis</th>
							<th class="p-4 text-right">Cena (zł)</th>
						</tr>
					</thead>
					<tbody>
						{#each mockItems as item}
							<tr class="hover:bg-primary/5 transition-colors border-b border-base-200">
								<th class="p-4 font-mono">{item.id}</th>
								<td class="p-4 font-semibold text-primary">{item.name}</td>
								<td class="p-4 text-base-content/80 italic">{item.description}</td>
								<td class="p-4 text-right font-bold text-secondary">{item.price.toFixed(2)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</section>
</div>
