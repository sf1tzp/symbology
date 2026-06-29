<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from 'mode-watcher';
	import Navbar from '$lib/components/Navbar.svelte';
	import MobileTabBar from '$lib/components/MobileTabBar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { env } from '$env/dynamic/public';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	let { children, data } = $props();

	// The Navbar (and its spacer) only ride the top on the home screen and at md+,
	// so on every other mobile page there's no top chrome to clear the notch —
	// <main> takes the top safe-area inset itself there. env() resolves to 0 at md+
	// and on un-notched devices, so the inset padding is a no-op off mobile.
	let isHome = $derived(page.url.pathname === resolve('/'));
</script>

<svelte:head>
	<title>Symbology — SEC Filing Synthesis</title>
	<meta
		name="description"
		content="Symbology synthesizes readable prose from large bodies of SEC filings — quarter by quarter, year by year, straight from primary sources."
	/>
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
<!--
	Top notch scrim — a fixed blurred band over the status-bar safe area on mobile.
	With viewport-fit=cover the layout extends behind the notch, so without this any
	content (or a just-below-the-notch sticky heading) scrolling through that band
	shows raw. The scrim keeps it a blurred backdrop, matching the bars. Zero-height
	(and so invisible) at md+ and on un-notched devices. Behind the home-screen nav.
-->
<div
	aria-hidden="true"
	class="pointer-events-none fixed inset-x-0 top-0 z-40 h-[env(safe-area-inset-top)] bg-background/80 backdrop-blur-md md:hidden"
></div>

<div
	class="page flex min-h-[100svh] flex-col bg-background pb-[calc(3.75rem+env(safe-area-inset-bottom))] md:pb-0"
>
	<Navbar user={data.user} supporter={data.supporter} avatarBadge={data.avatarBadge} />

	<!--
		w-full is load-bearing: <main> is a flex item of this column-flex wrapper,
		and .page's `margin-inline: auto` otherwise defeats the default stretch,
		letting <main> shrink-wrap to its widest content's intrinsic width (e.g. the
		featured-carousel's row of slides) and overflow the viewport horizontally.
	-->
	<main
		class="page w-full flex-1 py-4 md:py-8 {isHome
			? ''
			: 'pt-[calc(1rem+env(safe-area-inset-top))] md:pt-8'}"
	>
		{@render children?.()}
	</main>

	<Footer />

	<MobileTabBar user={data.user} avatarBadge={data.avatarBadge} />
</div>
