<script>
    import { user, updateProfile } from '$lib/auth.svelte.js';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';

    let display_name = $state('');
    let is_private = $state(false);
    let message = $state({ text: '', type: '' }); // type: 'success' | 'error'
    let isSaving = $state(false);

    // Sync data from profile when loaded
    $effect(() => {
        if (user.profile) {
            display_name = user.profile.display_name || '';
            is_private = user.profile.is_private ?? true;
        }
    });

    // Redirect if not logged in
    $effect(() => {
        if (!user.loading && !user.isLoggedIn) {
            goto('/auth');
        }
    });

    /** @param {SubmitEvent} e */
    async function handleSave(e) {
        e.preventDefault();
        isSaving = true;
        message = { text: '', type: '' };

        const result = await updateProfile({
            display_name,
            is_private
        });

        if (result.success) {
            message = { text: 'Profile successfully updated!', type: 'success' };
        } else {
            message = { text: result.message, type: 'error' };
        }
        isSaving = false;
        
        // Hide message after 4 seconds
        setTimeout(() => { message = { text: '', type: '' }; }, 4000);
    }
</script>

<div class="max-w-3xl mx-auto py-10 px-4 sm:px-6 lg:px-8">

    <div class="card bg-base-100 shadow-2xl border border-base-200/60">
        <div class="card-body p-6 sm:p-8">
            <form onsubmit={handleSave} class="flex flex-col gap-6">
                
                <div class="space-y-5">
                    <h2 class="text-xl font-bold border-b border-base-200 pb-2">Basic Information</h2>
                    
                    <div class="form-control w-full">
                        <label class="label" for="email">
                            <span class="label-text font-semibold text-base-content/70">Email Address</span>
                        </label>
                        <input 
                            id="email"
                            type="email" 
                            value={user.data?.email} 
                            class="input input-bordered w-full bg-base-200/50 text-base-content/60 cursor-not-allowed" 
                            disabled 
                        />
                        <label class="label" for="email">
                            <span class="label-text-alt text-base-content/50 flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" /></svg>
                                Email address cannot be changed.
                            </span>
                        </label>
                    </div>

                    <div class="form-control w-full">
                        <label class="label" for="display_name">
                            <span class="label-text font-semibold">Display Name</span>
                        </label>
                        <input 
                            id="display_name"
                            type="text" 
                            placeholder="e.g. Stormbringer" 
                            class="input input-bordered w-full focus:input-primary transition-colors" 
                            bind:value={display_name}
                        />
                    </div>
                </div>

                <div class="mt-4">
                    <h2 class="text-xl font-bold border-b border-base-200 pb-2 mb-4">Privacy</h2>
                    
                    <div class="form-control bg-base-100 border border-base-300 rounded-xl p-5 hover:border-primary/40 transition-colors shadow-sm">
                        <label class="cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div>
                                <span class="label-text font-bold text-lg flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-primary">
                                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    Private Profile
                                </span> 
                                <p class="text-sm text-base-content/60 mt-1">
                                    Hide your stats and items from other users.
                                </p>
                            </div>
                            <input type="checkbox" class="toggle toggle-primary toggle-lg" bind:checked={is_private} />
                        </label>
                    </div>
                </div>

                <div class="divider mt-2 mb-0"></div>
                <div class="card-actions justify-end mt-2">
                    <button class="btn btn-primary w-full sm:w-auto sm:btn-wide shadow-lg shadow-primary/30 transition-transform active:scale-95" disabled={isSaving}>
                        {#if isSaving}
                            <span class="loading loading-spinner loading-sm"></span>
                        {/if}
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </form>
        </div>
    </div>

    {#if message.text}
        <div 
            role="alert" 
            class="alert {message.type === 'success' ? 'alert-success' : 'alert-error'} mb-8 shadow-lg transition-all duration-300 animate-fade-in"
        >
            {#if message.type === 'success'}
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {:else}
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {/if}
            <span class="font-medium">{message.text}</span>
        </div>
    {/if}

</div>

<style>
    .animate-fade-in {
        animation: fadeIn 0.3s ease-out forwards;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
