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

            <div class="relative my-10">
                <div class="absolute inset-0 flex items-center"><span class="w-full border-t border-base-300"></span></div>
                <div class="relative flex justify-center text-xs uppercase"><span class="bg-base-100 px-4 text-base-content/30 font-bold tracking-widest">Or continue with</span></div>
            </div>

            <div class="grid grid-cols-2 gap-4">
                <button class="btn btn-outline btn-sm h-11 border-base-300 hover:bg-base-200 hover:text-base-content hover:border-base-300 gap-2 font-bold text-xs">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M15.545 6.558a9.42 9.42 0 0 1 .139 1.626c0 2.434-.87 4.492-2.384 5.885h.002C11.978 15.292 10.158 16 8 16A8 8 0 1 1 8 0a7.689 7.689 0 0 1 5.352 2.082l-2.284 2.284A4.347 4.347 0 0 0 8 3.166c-2.087 0-3.86 1.408-4.492 3.304a4.792 4.792 0 0 0 0 3.063c.632 1.896 2.405 3.304 4.492 3.304 1.108 0 2.04-.29 2.756-.783A3.714 3.714 0 0 0 12.57 10.11H8V7.04h7.545z"/></svg>
                    Google
                </button>
                <button class="btn btn-outline btn-sm h-11 border-base-300 hover:bg-base-200 hover:text-base-content hover:border-base-300 gap-2 font-bold text-xs">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
                    GitHub
                </button>
            </div>
        </div>
    </div>
</div>
