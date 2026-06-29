<script lang="ts">
	import { page } from '$app/state';
	import DarkmodeToggle from '$lib/components/DarkmodeToggle.svelte';
	import Mark from '$lib/components/Mark.svelte';
	import Activity from '@lucide/svelte/icons/activity';
	import { resolve } from '$app/paths';
	import { buildNavItems, isCurrentPath, initials, type NavUser } from '$lib/nav';
	import type { AmountBadge } from '$lib/supporter-plans';
	import { supportEnabled } from '$lib/features';

	/** Minimal supporter standing the navbar needs to label the Support affordance. */
	type SupporterState = { active: boolean; daysLeft: number } | null;

	let {
		user = null,
		supporter = null,
		avatarBadge = null
	}: { user?: NavUser; supporter?: SupporterState; avatarBadge?: AmountBadge | null } = $props();

	let scrollY = $state(0);

	let navItems = buildNavItems();
	let scrolled = $derived(scrollY > 50);

	// On mobile the top bar eats too much real estate, so it's shown only on the
	// home screen; everywhere else mobile relies on the bottom MobileTabBar. From
	// md up the bar is always visible.
	let isHome = $derived(page.url.pathname === resolve('/'));
</script>

<svelte:window bind:scrollY />

<nav
	class="page fixed top-0 right-0 left-0 z-50 pt-[env(safe-area-inset-top)] transition-all duration-200 {isHome
		? ''
		: 'hidden md:block'} {scrolled
		? 'border-b border-border bg-background/80 backdrop-blur-md'
		: 'border-b border-border bg-background'}"
>
	<div class="page flex-between my-2 h-14">
		<!-- Left: Logo mark + brand -->
		<div class="flex gap-8 align-baseline">
			<a href={resolve('/')} class="flex items-center gap-2 text-ink">
				<Mark size={22} />
				<span class="font-serif text-lg tracking-tight">Symbology</span>
				<!-- <span class="font-serif text-lg tracking-tight">symbology<span class="text-teal">.online</span></span> -->
			</a>

			<!-- Center: Desktop nav links (mobile uses the bottom tab bar instead) -->
			<div class="hidden items-center gap-6 md:flex">
				{#each navItems as item (item.href)}
					<a
						href={item.href}
						class="text-sm transition-colors {isCurrentPath(page.url.pathname, item.href)
							? 'font-medium text-ink'
							: 'text-ink-3 hover:text-ink'}"
					>
						{item.label}
					</a>
				{/each}
			</div>
		</div>

		<!--
			Right: dark mode toggle, plus the account status. The avatar / sign-in
			link is desktop-only — on mobile the same destination is a tab in the
			MobileTabBar, so the top bar stays uncluttered.
		-->
		<div class="flex items-center gap-3">
			<DarkmodeToggle />

			<!-- Status lives behind supporter status now; the button is the discovery
			     path (non-supporters get bounced to /support by the route guard). -->
			<a
				href={resolve('/status')}
				title="Status"
				aria-label="Status"
				class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-ink-3 no-underline transition-colors hover:text-ink"
			>
				<Activity class="h-[1.2rem] w-[1.2rem]" />
			</a>

			<!--
				Patronage affordance — always links to /support. Uses the same
				green-on-green styling whether or not the viewer is already a supporter;
				only the label changes. Shown across breakpoints (on mobile it rides the
				home-screen bar, where the top nav appears). Hidden entirely while the
				support surface is gated off pre-launch.
			-->
			{#if supportEnabled}
				<a
					href={resolve('/support')}
					class="inline-flex items-center gap-1.5 rounded-full bg-sage-2 px-3 py-1.5 font-mono text-[11.5px] font-semibold tracking-wide text-teal-2 no-underline transition hover:brightness-[0.98]"
				>
					<span class="h-1.5 w-1.5 rounded-full bg-teal-2"></span>
					{supporter?.active ? 'Supporter' : 'Support'}
				</a>
			{/if}

			{#if user}
				<a
					href={resolve('/a/watchlist')}
					title={avatarBadge ? `${user.name} · ${avatarBadge.label}` : user.name}
					aria-label="Account"
					class="hidden h-7 w-7 items-center justify-center rounded-full bg-sage-2 font-mono text-[11px] font-semibold text-teal-2 no-underline md:inline-flex"
				>
					{#if avatarBadge}
						<span class="text-[13px] leading-none">{avatarBadge.emoji}</span>
					{:else}
						{initials(user.name)}
					{/if}
				</a>
			{:else}
				<a
					href={resolve('/login')}
					class="hidden text-sm text-ink-3 no-underline transition-colors hover:text-ink md:inline-flex"
				>
					Sign in
				</a>
			{/if}
		</div>
	</div>
</nav>

<!-- Spacer to offset fixed navbar; collapses with the bar when it's hidden. Grows
     by the top safe-area inset so the bar's blur can extend behind the notch
     without pulling content underneath it (inset is 0 at md+ / un-notched). -->
<div class="{isHome ? '' : 'hidden md:block'} h-[calc(3.5rem+env(safe-area-inset-top))]"></div>
