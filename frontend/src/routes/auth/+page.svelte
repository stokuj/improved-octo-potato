<script>
    import { login, register, user } from '$lib/auth.svelte.js';

    let activeTab = $state('login'); // 'login' lub 'register'
    let email = $state('');
    let password = $state('');
    let errorMessage = $state('');
    let isLoading = $state(false);

    async function handleSubmit(e) {
        e.preventDefault();
        isLoading = true;
        errorMessage = '';

        const action = activeTab === 'login' ? login : register;
        const result = await action(email, password);

        if (!result.success) {
            errorMessage = result.message;
        }
        isLoading = false;
    }
</script>

<div class="flex justify-center items-center py-10 min-h-[60vh]">
    <div class="card bg-base-100 w-full max-w-md shadow-2xl border border-base-300">
        <div class="card-body">
            <!-- Tabs do przełączania -->
            <div role="tablist" class="tabs tabs-boxed mb-8 p-1">
                <button 
                    role="tab" 
                    class="tab transition-all {activeTab === 'login' ? 'tab-active font-bold text-white' : ''}" 
                    onclick={() => { activeTab = 'login'; errorMessage = ''; }}>Logowanie</button>
                <button 
                    role="tab" 
                    class="tab transition-all {activeTab === 'register' ? 'tab-active font-bold text-white' : ''}" 
                    onclick={() => { activeTab = 'register'; errorMessage = ''; }}>Rejestracja</button>
            </div>

            <h2 class="card-title text-3xl font-extrabold text-primary mb-2">
                {activeTab === 'login' ? 'Witaj ponownie!' : 'Stwórz nowe konto'}
            </h2>
            <p class="text-base-content/60 mb-6">
                {activeTab === 'login' ? 'Zaloguj się, aby kontynuować.' : 'Wypełnij dane, aby zacząć korzystać z AA Tracker.'}
            </p>

            {#if errorMessage}
                <div role="alert" class="alert alert-error mb-6 shadow-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{errorMessage}</span>
                </div>
            {/if}

            <form onsubmit={handleSubmit} class="space-y-4">
                <div class="form-control">
                    <label class="label"><span class="label-text font-semibold">Email</span></label>
                    <input 
                        type="email" 
                        placeholder="twoj@email.com" 
                        class="input input-bordered focus:input-primary" 
                        bind:value={email}
                        required 
                    />
                </div>

                <div class="form-control">
                    <label class="label"><span class="label-text font-semibold">Hasło</span></label>
                    <input 
                        type="password" 
                        placeholder="••••••••" 
                        class="input input-bordered focus:input-primary" 
                        bind:value={password}
                        required 
                    />
                </div>

                <button class="btn btn-primary w-full mt-8 shadow-lg shadow-primary/20" disabled={isLoading}>
                    {#if isLoading}
                        <span class="loading loading-spinner"></span>
                    {/if}
                    {activeTab === 'login' ? 'Zaloguj się' : 'Zarejestruj się'}
                </button>
            </form>

            <div class="divider text-xs text-base-content/40 mt-8 uppercase tracking-widest">Lub kontynuuj przez</div>

            <div class="grid grid-cols-2 gap-4">
                <button class="btn btn-outline btn-sm gap-2 opacity-60 hover:opacity-100">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M15.545 6.558a9.42 9.42 0 0 1 .139 1.626c0 2.434-.87 4.492-2.384 5.885h.002C11.978 15.292 10.158 16 8 16A8 8 0 1 1 8 0a7.689 7.689 0 0 1 5.352 2.082l-2.284 2.284A4.347 4.347 0 0 0 8 3.166c-2.087 0-3.86 1.408-4.492 3.304a4.792 4.792 0 0 0 0 3.063c.632 1.896 2.405 3.304 4.492 3.304 1.108 0 2.04-.29 2.756-.783A3.714 3.714 0 0 0 12.57 10.11H8V7.04h7.545z"/></svg>
                    Google
                </button>
                <button class="btn btn-outline btn-sm gap-2 opacity-60 hover:opacity-100">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
                    GitHub
                </button>
            </div>
        </div>
    </div>
</div>
