<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import DarkmodeToggle from '$lib/components/DarkmodeToggle.svelte';
	import {
		NavigationMenuRoot as NavigationMenu,
		NavigationMenuItem,
		NavigationMenuLink,
		NavigationMenuList
	} from '$lib/components/ui/navigation-menu';

	interface Props {
		currentPath: string;
	}

	let { currentPath }: Props = $props();

	const navItems = [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' },
		{ href: '/sectors', label: 'Sectors' },
		{ href: '/search', label: 'Search' },
		{ href: '/faq', label: 'FAQ' }
	];

	function isCurrentPath(href: string): boolean {
		if (href === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(href);
	}

	let mobileMenuOpen = $state(false);
</script>

<div class="border-b">
	<div class="mx-auto grid max-w-7xl grid-cols-12 gap-4 p-2">
		<NavigationMenu class="col-span-10">
			<Button
				variant="ghost"
				size="sm"
				class="pr-4 pl-0 lg:hidden"
				onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
			>
				<span class="text-lg">☰</span>
				<span class="sr-only">Toggle Menu</span>
			</Button>
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
		<div class="col-span-2 ml-auto">
			<DarkmodeToggle />
		</div>
	</div>
	<!-- Mobile dropdown menu -->
	{#if mobileMenuOpen}
		<div class="border-t bg-background px-4 py-2">
			<nav class="flex flex-col space-y-2">
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
</div>
