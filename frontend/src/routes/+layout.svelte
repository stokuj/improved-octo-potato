<script>
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
	<title>AA Tracker Svelte</title>
</svelte:head>

<div class="min-h-screen flex flex-col bg-base-200">
	<!-- Navbar -->
	<header class="navbar bg-base-100 shadow-md px-4">
		<div class="flex-1">
			<a href="/" class="btn btn-ghost normal-case text-xl font-bold">
				<span class="text-primary">AA</span> Tracker
			</a>
		</div>
		<div class="flex-none">
			<ul class="menu menu-horizontal px-1 gap-2 items-center">
				<li><a href="/items" class="hover:bg-primary/10">Przedmioty</a></li>
				<li><a href="/categories" class="hover:bg-primary/10">Kategorie</a></li>
				<li><a href="/about" class="hover:bg-primary/10">O nas</a></li>
				
				<div class="divider divider-horizontal mx-1"></div>

				{#if user.loading}
					<span class="loading loading-spinner loading-sm text-primary"></span>
				{:else if user.isLoggedIn}
					<div class="dropdown dropdown-end">
						<div tabindex="0" role="button" class="btn btn-ghost btn-circle avatar placeholder">
							<div class="bg-primary text-primary-content rounded-full w-10">
								<span>{user.data?.email?.[0].toUpperCase()}</span>
							</div>
						</div>
						<ul tabindex="0" class="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52">
							<li class="px-4 py-2 font-bold text-xs opacity-50">{user.data?.email}</li>
							<li><a href="/profile">Profil</a></li>
							<li><button onclick={logout} class="text-error">Wyloguj się</button></li>
						</ul>
					</div>
				{:else}
					<li>
						<a href="/auth" class="btn btn-primary btn-sm ml-2"> Zaloguj się </a>
					</li>
				{/if}
			</ul>
		</div>
	</header>

	<!-- Main Content -->
	<main class="container mx-auto my-8 p-6 flex-1 bg-base-100 rounded-box shadow-lg">
		{#if user.loading && !user.isLoggedIn}
			<div class="flex justify-center items-center h-64">
				<span class="loading loading-ring loading-lg text-primary"></span>
			</div>
		{:else}
			{@render children()}
		{/if}
	</main>

	<!-- Footer -->
	<footer class="footer footer-center p-6 bg-base-300 text-base-content">
		<aside>
			<p class="font-bold">AA Tracker Prototype</p> 
			<p>Copyright © {new Date().getFullYear()} - Wszelkie prawa zastrzeżone</p>
		</aside> 
		<nav class="grid-flow-col gap-4">
			<a href="/about" class="link link-hover">O nas</a>
			<a href="/#" class="link link-hover">Kontakt</a>
			<a href="https://github.com" class="link link-hover" target="_blank">GitHub</a>
		</nav>
	</footer>
</div>
