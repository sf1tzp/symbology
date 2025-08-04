<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { page } from '$app/stores';
	import Header from '$lib/components/Header.svelte';
	import Navigation from '$lib/components/ui/Navigation.svelte';

	let { children } = $props();
</script>

<ModeWatcher />

<div class="bg-background min-h-screen">
	<Header />

	<!-- Mobile-first navigation -->
	<Navigation currentPath={$page.url.pathname} />

	<main class="container mx-auto px-4 py-6">
		{@render children?.()}
	</main>
</div>
