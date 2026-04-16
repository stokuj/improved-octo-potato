<script>
	import { mockItems } from '$lib/mockData.js';
</script>

<div class="space-y-12">
	<!-- Hero section -->
	<section class="hero bg-gradient-to-br from-base-200 to-base-300 rounded-box p-12 shadow-inner overflow-hidden relative">
        <div class="absolute -right-20 -top-20 w-64 h-64 bg-primary/10 rounded-full blur-3xl"></div>
        <div class="absolute -left-20 -bottom-20 w-64 h-64 bg-secondary/10 rounded-full blur-3xl"></div>
        
		<div class="hero-content text-center relative z-10">
			<div class="max-w-2xl">
				<h1 class="text-6xl font-black text-primary tracking-tighter">AA Tracker <span class="text-base-content">Svelte</span></h1>
				<p class="py-6 text-xl text-base-content/70 font-medium">
					Najszybszy tracker cen przedmiotów z <span class="text-secondary font-bold">Item House</span>. Monitoruj rynek, śledź zmiany i optymalizuj swój ekwipunek.
				</p>
				<div class="flex gap-4 justify-center">
                    <a href="/items" class="btn btn-primary btn-lg shadow-xl hover:scale-105 transition-all">Przeglądaj Rynek</a>
                    <a href="/auth" class="btn btn-outline btn-lg hover:scale-105 transition-all">Dołącz do nas</a>
                </div>
			</div>
		</div>
	</section>

	<!-- Market Overview -->
	<section class="space-y-4">
        <div class="flex justify-between items-center px-2">
			<h2 class="text-2xl font-black uppercase tracking-widest opacity-80">Gorące Oferty</h2>
            <a href="/items" class="link link-primary no-underline font-bold text-sm">Zobacz wszystkie &rarr;</a>
        </div>
        
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each mockItems as item}
                <div class="card bg-base-100 shadow-md border border-base-200 hover:border-primary/50 transition-all cursor-pointer overflow-hidden">
                    <div class="card-body p-6">
                        <div class="flex justify-between items-start">
                            <h3 class="card-title text-primary">{item.name}</h3>
                            <div class="badge badge-success badge-sm font-bold">OKAZJA</div>
                        </div>
                        <p class="text-sm opacity-60 italic">{item.description}</p>
                        <div class="divider my-1 opacity-20"></div>
                        <div class="flex justify-between items-end">
                            <div class="text-2xl font-black text-secondary">{item.price.toLocaleString()} <span class="text-xs font-normal opacity-50">sreb.</span></div>
                            <button class="btn btn-xs btn-primary btn-outline">Śledź</button>
                        </div>
                    </div>
                </div>
            {/each}
		</div>
	</section>
</div>
