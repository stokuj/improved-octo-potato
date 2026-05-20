<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { user, checkMe, logout } from '$lib/auth.svelte.js';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		checkMe();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>AA Tracker</title>
</svelte:head>

<div class="min-h-screen flex flex-col bg-base-200" data-theme="night">
	<!-- Navbar -->
	<header class="navbar bg-base-100/80 backdrop-blur-md shadow-md px-4 sticky top-0 z-50 border-b border-base-300/50">
		<div class="flex-1">
			<a href="/" class="btn btn-ghost normal-case px-2 gap-2 group">
				<span class="text-2xl font-black tracking-tighter">
					<span class="text-primary">AA</span><span class="text-base-content">Tracker</span>
				</span>
				<span class="badge badge-xs badge-primary badge-outline font-black opacity-60 hidden sm:inline-flex">BETA</span>
			</a>
		</div>
		<div class="flex-none">
			<ul class="menu menu-horizontal px-1 gap-1 items-center">
				<li>
					<a href="/items" class="font-semibold text-sm hover:text-primary transition-colors">
						Market
					</a>
				</li>

				{#if user.loading}
					<span class="loading loading-spinner loading-xs text-primary ml-2"></span>
				{:else if user.isLoggedIn}
					<li>
						<a href="/saved-items" class="font-semibold text-sm hover:text-primary transition-colors">
							Watchlist
						</a>
					</li>
					<li>
						<a href="/inventory" class="font-semibold text-sm hover:text-primary transition-colors">
							Inventory
						</a>
					</li>
					<div class="dropdown dropdown-end ml-1">
						<div tabindex="0" role="button" class="btn btn-ghost btn-sm btn-circle avatar placeholder">
							<div class="bg-primary/20 text-primary rounded-full w-8 border border-primary/30">
								<span class="text-xs font-black">{user.data?.email?.[0].toUpperCase()}</span>
							</div>
						</div>
						<ul class="mt-3 z-[1] p-2 shadow-xl menu menu-sm dropdown-content bg-base-100 rounded-box w-52 border border-base-300">
							<li class="px-3 py-2">
								<span class="font-bold text-xs opacity-40 uppercase tracking-wider truncate">{user.data?.email}</span>
							</li>
							<li><a href="/settings" class="text-sm">Settings</a></li>
							<li>
								<button onclick={logout} class="text-error text-sm border-t border-base-300 mt-1 pt-2 rounded-none">
									Sign Out
								</button>
							</li>
						</ul>
					</div>
				{:else}
					<li>
						<a href="/auth" class="btn btn-primary btn-sm ml-1 font-bold">Sign In</a>
					</li>
				{/if}
			</ul>
		</div>
	</header>

	<!-- Main Content -->
	<main class="container mx-auto my-6 p-4 sm:p-6 flex-1 bg-base-100 rounded-box shadow-lg">
		{#if user.loading && !user.isLoggedIn}
			<div class="flex justify-center items-center h-64">
				<span class="loading loading-ring loading-lg text-primary"></span>
			</div>
		{:else}
			{@render children()}
		{/if}
	</main>

	<!-- Footer -->
	<footer class="footer footer-center p-6 bg-base-200 text-base-content/40 text-xs border-t border-base-300/50">
		<div class="flex flex-wrap gap-6 justify-center items-center">
			<span class="font-black uppercase tracking-widest">AA Tracker</span>
			<div class="flex gap-4">
				<a href="/about" class="link link-hover">About</a>
				<a href="https://github.com/stokuj/improved-octo-potato" class="link link-hover" target="_blank">GitHub</a>
			</div>
		</div>
	</footer>
</div>
