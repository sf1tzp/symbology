<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from 'mode-watcher';
	import Navbar from '$lib/components/Navbar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { env } from '$env/dynamic/public';
	let { children } = $props();
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

<div class="page flex min-h-screen flex-col bg-background">
	<Navbar />

	<main class="page flex-1 py-8">
		{@render children?.()}
	</main>

	<Footer />
</div>
