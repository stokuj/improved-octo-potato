<script lang="ts">
    import { onMount } from 'svelte';
    import { finishGoogleLogin, getUserState } from '$lib/core/auth.svelte.js';

    const user = getUserState();

    let errorMessage = $state('');

    onMount(async () => {
        const result = await finishGoogleLogin(user, window.location.search);
        if (!result.success) {
            errorMessage = result.message ?? 'Google sign-in failed. Try again.';
        }
    });
</script>

<div class="flex justify-center items-center py-12 min-h-[70vh]">
    {#if errorMessage}
        <div class="card bg-base-100 w-full max-w-[440px] shadow-xl border border-base-200">
            <div class="card-body p-10 gap-6">
                <div role="alert" class="alert alert-error text-sm">
                    <span>{errorMessage}</span>
                </div>
                <a href="/auth" class="btn btn-ghost">Back to sign in</a>
            </div>
        </div>
    {:else}
        <span class="loading loading-spinner loading-lg" aria-label="Signing in"></span>
    {/if}
</div>
