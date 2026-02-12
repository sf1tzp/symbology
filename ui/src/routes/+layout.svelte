<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { page } from '$app/state';
	import Navbar from '$lib/components/Navbar.svelte';
	import Footer from '$lib/components/Footer.svelte';

	let { children } = $props();

	let isLanding = $derived(page.url.pathname === '/');
</script>

<svelte:head>
	<title>Symbology - Investment Analysis Platform</title>
	<meta name="description" content="Explore LLM-generated insights on publicly traded companies." />
</svelte:head>

<ModeWatcher />

<div class="flex min-h-screen flex-col bg-background">
	<Navbar />

	{#if isLanding}
		<main class="flex-1">
			{@render children?.()}
		</main>
	{:else}
		<main class="container mx-auto flex-1 px-4 py-8 lg:max-w-7xl">
			{@render children?.()}
		</main>
	{/if}

	<Footer />
</div>
