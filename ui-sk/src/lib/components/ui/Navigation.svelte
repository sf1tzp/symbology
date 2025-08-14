<!-- Navigation.svelte -->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import {
		NavigationMenuRoot as NavigationMenu,
		NavigationMenuContent,
		NavigationMenuItem,
		NavigationMenuLink,
		NavigationMenuList,
		NavigationMenuTrigger
	} from '$lib/components/ui/navigation-menu';

	interface Props {
		currentPath: string;
	}

	let { currentPath }: Props = $props();

	// Navigation items
	const navItems = [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' }
		// { href: '/filings', label: 'Filings' },
		// { href: '/analysis', label: 'Analysis' }
	];

	function isCurrentPath(href: string): boolean {
		if (href === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(href);
	}

	function handleNavigation(href: string) {
		goto(href);
	}

	// Mobile menu state
	let mobileMenuOpen = $state(false);
</script>

<!-- Mobile navigation -->
<div
	class="bg-background/95 supports-[backdrop-filter]:bg-background/60 border-b backdrop-blur lg:hidden"
>
	<div class="flex h-14 items-center px-4">
		<Button
			variant="ghost"
			size="sm"
			class="mr-2 px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 lg:hidden"
			onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
		>
			<span class="text-lg">☰</span>
			<span class="sr-only">Toggle Menu</span>
		</Button>

		<div class="flex flex-1">
			<nav class="flex items-center space-x-1">
				{#each navItems as item}
					<Button
						variant={isCurrentPath(item.href) ? 'secondary' : 'ghost'}
						size="sm"
						onclick={() => handleNavigation(item.href)}
					>
						{item.label}
					</Button>
				{/each}
			</nav>
		</div>
	</div>

	<!-- Mobile dropdown menu -->
	{#if mobileMenuOpen}
		<div class="bg-background border-t px-4 py-2">
			<nav class="flex flex-col space-y-2">
				{#each navItems as item}
					<Button
						variant={isCurrentPath(item.href) ? 'secondary' : 'ghost'}
						class="justify-start"
						onclick={() => {
							handleNavigation(item.href);
							mobileMenuOpen = false;
						}}
					>
						{item.label}
					</Button>
				{/each}
			</nav>
		</div>
	{/if}
</div>

<!-- Desktop navigation -->
<div
	class="bg-background/95 supports-[backdrop-filter]:bg-background/60 hidden border-b backdrop-blur lg:block"
>
	<div class="container flex h-14 items-center">
		<NavigationMenu class="mx-6">
			<NavigationMenuList>
				{#each navItems as item}
					<NavigationMenuItem>
						<NavigationMenuLink
							href={item.href}
							class="bg-background hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground group inline-flex h-9 w-max items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none disabled:pointer-events-none disabled:opacity-50 {isCurrentPath(
								item.href
							)
								? 'text-foreground font-semibold'
								: 'text-muted-foreground'}"
						>
							{item.label}
						</NavigationMenuLink>
					</NavigationMenuItem>
				{/each}
			</NavigationMenuList>
		</NavigationMenu>
	</div>
</div>
