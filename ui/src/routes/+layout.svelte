<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from 'mode-watcher';
	import { page } from '$app/state';
	import Navbar from '$lib/components/Navbar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { env } from '$env/dynamic/public';
	let { children } = $props();

	let isLanding = $derived(page.url.pathname === '/');
</script>

<svelte:head>
	<title>Symbology - Investment Analysis Platform</title>
	<meta name="description" content="Explore LLM-generated insights on publicly traded companies." />
	<link rel="icon" href={favicon} />
	<script
		defer
		src={env.PUBLIC_UMAMI_SCRIPT_URL}
		data-website-id={env.PUBLIC_UMAMI_WEBSITE_ID}
		data-performance="true"
	></script>
</svelte:head>

<ModeWatcher />

<div class="flex min-h-screen flex-col bg-background">
	<Navbar />

	{#if isLanding}
		<main class="flex-1">
			{@render children?.()}
		</main>
	{:else}
		<main class="page flex-1 py-8">
			{@render children?.()}
		</main>
	{/if}

	<Footer />
</div>
