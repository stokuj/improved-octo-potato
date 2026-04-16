<script>
    import { user } from '$lib/auth.svelte.js';
    import { goto } from '$app/navigation';

    // Mock danych dla "Mojego Ekwipunku" - przedmioty śledzone przez użytkownika
    let myItems = $state([
        { 
            id: 101, 
            name: "Luksusowy Miecz Królewski", 
            currentPrice: 12500, 
            oldPrice: 11000, 
            change: 13.6,
            lastUpdate: "2 minuty temu",
            rarity: "Legendarny"
        },
        { 
            id: 102, 
            name: "Tarcza Smoczego Blasku", 
            currentPrice: 8400, 
            oldPrice: 9200, 
            change: -8.7,
            lastUpdate: "15 minut temu",
            rarity: "Rzadki"
        },
        { 
            id: 103, 
            name: "Mikstura Wielkiej Mocy", 
            currentPrice: 450, 
            oldPrice: 450, 
            change: 0,
            lastUpdate: "1 godzina temu",
            rarity: "Pospolity"
        }
    ]);

    // Przekierowanie jeśli nie zalogowany
    $effect(() => {
        if (!user.loading && !user.isLoggedIn) {
            goto('/auth');
        }
    });
</script>

<div class="space-y-6">
    <div class="flex justify-between items-end border-b border-base-300 pb-4">
        <div>
            <h1 class="text-3xl font-black text-primary">Mój Ekwipunek</h1>
            <p class="text-base-content/60">Śledzone ceny przedmiotów z Item House</p>
        </div>
        <div class="stats shadow bg-base-200 hidden md:flex">
            <div class="stat py-2 px-4">
                <div class="stat-title text-xs uppercase">Śledzone</div>
                <div class="stat-value text-lg text-primary">{myItems.length}</div>
            </div>
        </div>
    </div>

    {#if !user.isLoggedIn}
        <div class="hero bg-base-200 rounded-box p-10">
            <div class="hero-content text-center">
                <div class="max-w-md">
                    <h2 class="text-2xl font-bold">Zaloguj się, aby śledzić ceny</h2>
                    <p class="py-4 text-base-content/70">Tylko zalogowani użytkownicy mogą dodawać przedmioty do swojego ekwipunku i monitorować ich zmiany.</p>
                    <a href="/auth" class="btn btn-primary">Przejdź do logowania</a>
                </div>
            </div>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each myItems as item}
                <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all border border-base-200 group">
                    <div class="card-body p-5">
                        <div class="flex justify-between items-start mb-2">
                            <span class="badge badge-sm font-bold {
                                item.rarity === 'Legendarny' ? 'badge-warning' : 
                                item.rarity === 'Rzadki' ? 'badge-info' : 'badge-ghost'
                            }">{item.rarity}</span>
                            <button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity">Usuń</button>
                        </div>
                        
                        <h2 class="card-title text-lg leading-tight mb-4">{item.name}</h2>
                        
                        <div class="flex items-center justify-between bg-base-200/50 p-3 rounded-lg">
                            <div>
                                <div class="text-xs uppercase opacity-50 font-bold">Cena</div>
                                <div class="text-xl font-black">{item.currentPrice.toLocaleString()} <span class="text-xs font-normal">sreb.</span></div>
                            </div>
                            <div class="text-right">
                                <div class="text-xs uppercase opacity-50 font-bold">Zmiana</div>
                                <div class="flex items-center gap-1 font-bold {item.change > 0 ? 'text-error' : item.change < 0 ? 'text-success' : ''}">
                                    {#if item.change > 0}
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
                                        </svg>
                                    {:else if item.change < 0}
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1V9a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586 3.707 5.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L11 9.414 14.586 13H12z" clip-rule="evenodd" />
                                        </svg>
                                    {/if}
                                    {item.change > 0 ? '+' : ''}{item.change}%
                                </div>
                            </div>
                        </div>

                        <div class="card-actions justify-between items-center mt-4">
                            <span class="text-[10px] uppercase opacity-40 font-bold">Aktualizacja: {item.lastUpdate}</span>
                            <a href="/items/{item.id}" class="btn btn-sm btn-ghost border border-base-300">Szczegóły</a>
                        </div>
                    </div>
                </div>
            {/each}
            
        </div>
    {/if}
</div>
