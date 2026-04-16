<script>
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>AA Tracker Svelte</title>
</svelte:head>

<div class="min-h-screen flex flex-col bg-base-200">
	<!-- Navbar -->
	<header class="navbar bg-base-100 shadow-md px-4">
		<div class="flex-1">
			<a href="/" class="btn btn-ghost normal-case text-xl font-bold">AA Tracker Svelte</a>
		</div>
		<div class="flex-none">
			<ul class="menu menu-horizontal px-1 gap-2">
				<li><a href="/items" class="hover:bg-primary/10">Przedmioty</a></li>
				<li><a href="/categories" class="hover:bg-primary/10">Kategorie</a></li>
				<li><a href="/about" class="hover:bg-primary/10">O nas</a></li>
				<li>
					<a href="/auth" class="btn btn-primary btn-sm ml-2"> Zaloguj się </a>
				</li>
			</ul>
		</div>
	</header>

	<!-- Main Content -->
	<main class="container mx-auto my-8 p-6 flex-1 bg-base-100 rounded-box shadow-lg">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="footer footer-center p-6 bg-base-300 text-base-content">
		<aside>
			<p class="font-bold">
				AA Tracker Prototype
			</p> 
			<p>Copyright © {new Date().getFullYear()} - Wszelkie prawa zastrzeżone</p>
		</aside> 
		<nav class="grid-flow-col gap-4">
			<a href="/about" class="link link-hover">O nas</a>
			<a href="/#" class="link link-hover">Kontakt</a>
			<a href="https://github.com" class="link link-hover" target="_blank">GitHub</a>
		</nav>
	</footer>
</div>
