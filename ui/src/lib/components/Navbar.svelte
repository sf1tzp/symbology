<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import DarkmodeToggle from '$lib/components/DarkmodeToggle.svelte';
	import {
		NavigationMenuRoot as NavigationMenu,
		NavigationMenuItem,
		NavigationMenuLink,
		NavigationMenuList
	} from '$lib/components/ui/navigation-menu';
	import Menu from '@lucide/svelte/icons/menu';
	import X from '@lucide/svelte/icons/x';

	let scrollY = $state(0);
	let mobileMenuOpen = $state(false);

	const navItems = [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' },
		{ href: '/groups', label: 'Groups' },
		{ href: '/search', label: 'Search' },
		{ href: '/faq', label: 'FAQ' }
	];

	function isCurrentPath(href: string): boolean {
		if (href === '/') {
			return page.url.pathname === '/';
		}
		return page.url.pathname.startsWith(href);
	}

	let scrolled = $derived(scrollY > 50);
</script>

<svelte:window bind:scrollY />

<nav
	class="fixed top-0 right-0 left-0 z-50 transition-all duration-200 {scrolled
		? 'border-b border-border bg-background/80 backdrop-blur-md'
		: 'border-b border-border bg-card'}"
>
	<div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
		<!-- Left: Logo + brand -->
		<a href="/" class="flex items-center gap-2">
			<img src="https://i.imgur.com/UeEDuUi.png" alt="Symbology Logo" class="h-8 w-auto rounded" />
			<span class="text-lg font-semibold tracking-wide text-primary">symbology</span>
		</a>

		<!-- Center-right: Desktop nav links -->
		<div class="hidden md:flex md:items-center md:gap-1">
			<NavigationMenu>
				<NavigationMenuList>
					{#each navItems as item}
						<NavigationMenuItem>
							<NavigationMenuLink
								href={item.href}
								class="font-medium transition-colors focus:outline-none {isCurrentPath(item.href)
									? 'font-semibold text-foreground'
									: 'text-muted-foreground'}"
							>
								{item.label}
							</NavigationMenuLink>
						</NavigationMenuItem>
					{/each}
				</NavigationMenuList>
			</NavigationMenu>
		</div>

		<!-- Right: Dark mode toggle + mobile hamburger -->
		<div class="flex items-center gap-2">
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

	<!-- Mobile dropdown menu -->
	{#if mobileMenuOpen}
		<div class="border-t bg-background px-4 py-2 md:hidden">
			<nav class="flex flex-col space-y-1">
				{#each navItems as item}
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
<div class="h-16"></div>
