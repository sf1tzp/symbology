<script lang="ts">
	import { page } from '$app/state';
	import DarkmodeToggle from '$lib/components/DarkmodeToggle.svelte';
	import Mark from '$lib/components/Mark.svelte';
	import { resolve } from '$app/paths';
	import { buildNavItems, isCurrentPath, initials, type NavUser } from '$lib/nav';

	let { user = null }: { user?: NavUser } = $props();

	let scrollY = $state(0);

	// Same user-aware model the MobileTabBar uses, so the two stay in sync.
	let navItems = $derived(buildNavItems(user));
	let scrolled = $derived(scrollY > 50);
</script>

<svelte:window bind:scrollY />

<nav
	class="page fixed top-0 right-0 left-0 z-50 transition-all duration-200 {scrolled
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

			{#if user}
				<a
					href={resolve('/account')}
					title={user.name}
					aria-label="Account"
					class="hidden h-7 w-7 items-center justify-center rounded-full bg-sage-2 font-mono text-[11px] font-semibold text-teal-2 no-underline md:inline-flex"
				>
					{initials(user.name)}
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

<!-- Spacer to offset fixed navbar -->
<div class="h-14"></div>
