<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { page } from '$app/stores'; // fixme: deprecated
	import Header from '$lib/components/Header.svelte';
	import Navigation from '$lib/components/ui/Navigation.svelte';

	let { children } = $props();
</script>

<ModeWatcher />

<div class="min-h-screen bg-background">
	<Header />

	<!-- Mobile-first navigation -->
	<Navigation currentPath={$page.url.pathname} />

	<main class="container mx-auto px-4 py-6 lg:max-w-7xl">
		{@render children?.()}
	</main>
</div>
