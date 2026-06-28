<script lang="ts">
	import { page } from '$app/state';
	import { buildMobileTabItems, companyContextTicker, isCurrentPath, type NavUser } from '$lib/nav';
	import House from '@lucide/svelte/icons/house';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Heart from '@lucide/svelte/icons/heart';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import CircleUser from '@lucide/svelte/icons/circle-user';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	let { user = null }: { user?: NavUser } = $props();

	// One icon per nav destination, keyed by href so it tracks the nav model.
	// Company-context links (/c/…) fall through to the Building2 default.
	const icons: Record<string, typeof House> = {
		'/': House,
		'/companies': Building2,
		'/support': Heart,
		'/faq': CircleQuestionMark,
		'/a/watchlist': CircleUser,
		'/login': LogIn
	};

	// On a company-context route (company/filing/document), the center slot becomes
	// a quick link back to the company; otherwise it's the Support CTA.
	let ticker = $derived(companyContextTicker(page.url.pathname, page.data));
	let items = $derived(buildMobileTabItems(user, ticker));
</script>

<!--
	Bottom tab bar — the primary navigation on mobile (replaces the top hamburger
	below `md`). Hidden at `md` and up, where the Navbar's inline links take over.
	The home-indicator gap is handled with `env(safe-area-inset-bottom)`.
-->
<nav
	class="fixed inset-x-0 bottom-0 z-50 flex items-stretch justify-around border-t border-border bg-background/80 pt-1.5 pb-[calc(0.25rem+env(safe-area-inset-bottom))] backdrop-blur-md md:hidden {mobileTabBar.hidden
		? 'hidden'
		: ''}"
	aria-label="Primary"
>
	{#each items as item (item.href)}
		{@const active = isCurrentPath(page.url.pathname, item.href)}
		{@const Icon = icons[item.href] ?? Building2}
		<a
			href={item.href}
			aria-current={active ? 'page' : undefined}
			class="flex flex-1 flex-col items-center gap-1 px-1 py-1 text-[9.5px] font-medium tracking-wide no-underline transition-colors {active
				? 'text-ink'
				: 'text-ink-4'}"
		>
			<Icon class="h-[21px] w-[21px] {active ? 'text-teal-2' : ''}" />
			{item.label}
		</a>
	{/each}
</nav>
