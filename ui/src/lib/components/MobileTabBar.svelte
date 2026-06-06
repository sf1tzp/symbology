<script lang="ts">
	import { page } from '$app/state';
	import {
		buildNavItems,
		accountNavItem,
		companyNavItem,
		companyContextTicker,
		isCurrentPath,
		type NavUser
	} from '$lib/nav';
	import House from '@lucide/svelte/icons/house';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Star from '@lucide/svelte/icons/star';
	import Activity from '@lucide/svelte/icons/activity';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import CircleUser from '@lucide/svelte/icons/circle-user';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	let { user = null }: { user?: NavUser } = $props();

	// One icon per nav destination, keyed by href so it tracks the nav model.
	const icons: Record<string, typeof House> = {
		'/': House,
		'/companies': Building2,
		'/watchlist': Star,
		'/status': Activity,
		'/faq': CircleQuestionMark,
		'/account': CircleUser,
		'/login': LogIn
	};

	// Same destinations as the desktop Navbar, plus the account/sign-in entry
	// the Navbar shows as an avatar — surfaced here as a trailing tab so mobile
	// users can reach their account without a separate menu.
	let baseItems = $derived([...buildNavItems(user), accountNavItem(user)]);

	// On a company-context route (company/filing/document), swap the center Status
	// tab for a quick link back to the company's main page.
	let ticker = $derived(companyContextTicker(page.url.pathname, page.data));
	let items = $derived(
		ticker
			? baseItems.map((item) => (item.href === '/status' ? companyNavItem(ticker) : item))
			: baseItems
	);
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
