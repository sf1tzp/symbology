<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import DarkmodeToggle from '$lib/components/DarkmodeToggle.svelte';
	import Mark from '$lib/components/Mark.svelte';
	import Menu from '@lucide/svelte/icons/menu';
	import X from '@lucide/svelte/icons/x';
	import { resolve } from '$app/paths';

	let scrollY = $state(0);
	let mobileMenuOpen = $state(false);

	const navItems = [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' },
		{ href: '/groups', label: 'Sectors' },
		// { href: '/search', label: 'Search' },
		{ href: '/faq', label: 'FAQ' }
	];

	function isCurrentPath(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}

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
			</a>

			<!-- Center: Desktop nav links -->
			<div class="hidden items-center gap-6 md:flex">
				{#each navItems as item (item.href)}
					<a
						href={resolve(item.href)}
						class="text-sm transition-colors {isCurrentPath(item.href)
							? 'font-medium text-ink'
							: 'text-ink-3 hover:text-ink'}"
					>
						{item.label}
					</a>
				{/each}
			</div>
		</div>

		<!-- Right: Search button + dark mode + mobile hamburger -->
		<div class="flex items-center gap-3">
			<!-- <a -->
			<!-- 	href={resolve('/search')} -->
			<!-- 	class="hidden items-center gap-2 rounded-md border border-rule bg-paper-2 px-3 py-1.5 text-sm text-ink-3 no-underline transition-colors hover:border-rule-2 hover:text-ink-2 md:flex" -->
			<!-- > -->
			<!-- 	<Search class="h-3.5 w-3.5" /> -->
			<!-- 	<span>Search companies, filings&hellip;</span> -->
			<!-- 	<kbd -->
			<!-- 		class="ml-2 rounded border border-rule bg-background px-1.5 py-0.5 font-mono text-[10px] text-ink-4" -->
			<!-- 		>&#8984;K</kbd -->
			<!-- 	> -->
			<!-- </a> -->
			<DarkmodeToggle />
			<Button
				variant="ghost"
				size="icon"
				class="md:hidden"
				onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
			>
				{#if mobileMenuOpen}
					<X class="h-5 w-5" />
				{:else}
					<Menu class="h-5 w-5" />
				{/if}
				<span class="sr-only">Toggle Menu</span>
			</Button>
		</div>
	</div>

	<!-- Mobile dropdown -->
	{#if mobileMenuOpen}
		<div class="border-t border-border bg-background px-4 py-2 md:hidden">
			<nav class="flex flex-col space-y-1">
				{#each navItems as item (item.href)}
					<Button
						variant={isCurrentPath(item.href) ? 'secondary' : 'ghost'}
						class="justify-start"
						onclick={() => {
							goto(item.href);
							mobileMenuOpen = false;
						}}
					>
						{item.label}
					</Button>
				{/each}
			</nav>
		</div>
	{/if}
</nav>

<!-- Spacer to offset fixed navbar -->
<div class="h-14"></div>
