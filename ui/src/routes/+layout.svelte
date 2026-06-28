<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from 'mode-watcher';
	import Navbar from '$lib/components/Navbar.svelte';
	import MobileTabBar from '$lib/components/MobileTabBar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { env } from '$env/dynamic/public';
	let { children, data } = $props();
</script>

<svelte:head>
	<title>Symbology — SEC Filing Synthesis</title>
	<meta
		name="description"
		content="Symbology synthesizes readable prose from large bodies of SEC filings — quarter by quarter, year by year, straight from primary sources."
	/>
	<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
	<link rel="icon" href={favicon} />
	<script
		defer
		src={env.PUBLIC_UMAMI_SCRIPT_URL}
		data-website-id={env.PUBLIC_UMAMI_WEBSITE_ID}
		data-performance="true"
	></script>
</svelte:head>

<ModeWatcher />

<!--
	The mobile bottom padding clears the fixed MobileTabBar. It sits on the outer
	container (below the footer, the last in-flow element) so nothing is hidden
	behind the bar when scrolled to the end. Removed at md, where the bar is gone.
-->
<div
	class="page flex min-h-screen flex-col bg-background pb-[calc(3.75rem+env(safe-area-inset-bottom))] md:pb-0"
>
	<Navbar user={data.user} supporter={data.supporter} avatarBadge={data.avatarBadge} />

	<!--
		w-full is load-bearing: <main> is a flex item of this column-flex wrapper,
		and .page's `margin-inline: auto` otherwise defeats the default stretch,
		letting <main> shrink-wrap to its widest content's intrinsic width (e.g. the
		featured-carousel's row of slides) and overflow the viewport horizontally.
	-->
	<main class="page w-full flex-1 py-4 md:py-8">
		{@render children?.()}
	</main>

	<Footer />

	<MobileTabBar user={data.user} />
</div>
