<script>
    import { login, register, user } from '$lib/auth.svelte.js';

    let activeTab = $state('login'); // 'login' or 'register'
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

<div class="flex justify-center items-center py-12 min-h-[70vh] bg-base-200/30 rounded-box">
    <div class="card bg-base-100 w-full max-w-[440px] shadow-xl border border-base-200">
        <div class="card-body p-10">
            <!-- Segmented Control (Tabs) -->
            <div class="bg-base-200 p-1.5 rounded-xl flex mb-10">
                <button 
                    class="flex-1 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 {activeTab === 'login' ? 'bg-base-100 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content hover:bg-base-300/50'}" 
                    onclick={() => { activeTab = 'login'; errorMessage = ''; }}>
                    Login
                </button>
                <button 
                    class="flex-1 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 {activeTab === 'register' ? 'bg-base-100 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content hover:bg-base-300/50'}" 
                    onclick={() => { activeTab = 'register'; errorMessage = ''; }}>
                    Register
                </button>
            </div>

            <div class="text-center mb-8">
                <p class="text-sm text-base-content/50 px-4">
                    {activeTab === 'login' ? 'Enter your credentials to access your market tracker.' : 'Create an account to start monitoring item prices.'}
                </p>
            </div>

            {#if errorMessage}
                <div role="alert" class="alert alert-error mb-8 py-3 rounded-xl shadow-sm text-xs font-medium">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{errorMessage}</span>
                </div>
            {/if}

            <form onsubmit={handleSubmit} class="space-y-5 w-full">
                <div class="form-control w-full">
                    <label class="label pt-0" for="email">
                        <span class="label-text font-bold text-xs uppercase opacity-40 tracking-widest">Email Address</span>
                    </label>
                    <input 
                        id="email"
                        type="email" 
                        placeholder="name@company.com" 
                        class="input input-bordered w-full focus:input-primary bg-base-200/30 border-base-300" 
                        bind:value={email}
                        required 
                    />
                </div>

                <div class="form-control w-full">
                    <label class="label pt-0" for="password">
                        <span class="label-text font-bold text-xs uppercase opacity-40 tracking-widest">Password</span>
                    </label>
                    <input 
                        id="password"
                        type="password" 
                        placeholder="••••••••" 
                        class="input input-bordered w-full focus:input-primary bg-base-200/30 border-base-300" 
                        bind:value={password}
                        required 
                    />
                </div>

                <button class="btn btn-primary w-full mt-4 h-12 shadow-md shadow-primary/10 font-bold" disabled={isLoading}>
                    {#if isLoading}
                        <span class="loading loading-spinner loading-sm"></span>
                    {/if}
                    {activeTab === 'login' ? 'Sign In' : 'Create Account'}
                </button>
            </form>

            <p class="text-center text-xs opacity-30 mt-6 font-bold uppercase tracking-widest">
                AA Tracker — ArcheAge Market Monitor
            </p>
        </div>
    </div>
</div>
