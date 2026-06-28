<script lang="ts">
	import { page } from '$app/state';
	import {
		buildMobileTabItems,
		buildContextNavItem,
		browseDestination,
		currentSection,
		siblingSections,
		isBrowseIndex,
		isCurrentPath,
		type NavItem,
		type BrowseSection,
		type ContextKind,
		type NavUser
	} from '$lib/nav';
	import Building2 from '@lucide/svelte/icons/building-2';
	import FileSearchCorner from '@lucide/svelte/icons/file-search-corner';
	import AudioWaveform from '@lucide/svelte/icons/audio-waveform';
	import Warehouse from '@lucide/svelte/icons/warehouse';
	import FileText from '@lucide/svelte/icons/file-text';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Heart from '@lucide/svelte/icons/heart';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import CircleUser from '@lucide/svelte/icons/circle-user';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	let { user = null }: { user?: NavUser } = $props();

	// Per-section identity for the leading browse tab and its flyout tags: the
	// surface icon plus the accent colour (app.css tokens) shared between them.
	const sections: Record<BrowseSection, { icon: typeof Building2; color: string }> = {
		companies: { icon: Building2, color: 'var(--teal-2)' },
		filings: { icon: FileSearchCorner, color: 'var(--blue)' },
		synthesis: { icon: AudioWaveform, color: 'var(--plum)' }
	};

	// Icon for the context slot, by the kind of resource it links back to.
	const contextIcons: Record<ContextKind, typeof Building2> = {
		company: Warehouse,
		filing: FileText,
		synthesis: Sparkles
	};

	// One icon per remaining static destination, keyed by href.
	const icons: Record<string, typeof Building2> = {
		'/support': Heart,
		'/faq': CircleQuestionMark,
		'/a/watchlist': CircleUser,
		'/login': LogIn
	};

	let section = $derived(currentSection(page.url.pathname));
	let browse = $derived(browseDestination(section));

	function iconFor(item: NavItem, isBrowseTab: boolean): typeof Building2 {
		if (isBrowseTab) return sections[section].icon;
		if ('kind' in item) return contextIcons[(item as { kind: ContextKind }).kind];
		return icons[item.href] ?? Building2;
	}

	// The context slot belongs to a browse section, so its icon takes the same
	// accent colour as that section's tab and flyout tag.
	const kindSection: Record<ContextKind, BrowseSection> = {
		company: 'companies',
		filing: 'filings',
		synthesis: 'synthesis'
	};

	// The section accent colour for an icon, or null for the plain static tabs
	// (FAQ / Support / Account), which keep the default active-teal treatment.
	function iconColor(item: NavItem, isBrowseTab: boolean): string | null {
		if (isBrowseTab) return sections[section].color;
		if ('kind' in item) return sections[kindSection[(item as { kind: ContextKind }).kind]].color;
		return null;
	}

	// On a resource route (company / filing / synthesis), the context slot links
	// back to that resource; otherwise it's FAQ.
	let context = $derived(buildContextNavItem(page.url.pathname, page.data));
	let items = $derived(buildMobileTabItems(user, context, browse));

	// The leading browse tab opens a flyout onto the sibling surfaces while the
	// viewer is on a browse index page; on detail pages it links back to the
	// section index instead (so the flyout pattern repeats one level up).
	let flyoutOpen = $state(false);
	let onBrowseIndex = $derived(isBrowseIndex(page.url.pathname));
	let flyout = $derived(siblingSections(section));
	// Close the flyout whenever the route changes (reading pathname registers it
	// as the effect's dependency).
	$effect(() => {
		if (page.url.pathname) flyoutOpen = false;
	});
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
	{#each items as item, i (item.href)}
		{@const isBrowseTab = i === 0}
		{@const active = isCurrentPath(page.url.pathname, item.href)}
		{@const Icon = iconFor(item, isBrowseTab)}
		{@const color = iconColor(item, isBrowseTab)}
		{#if isBrowseTab && onBrowseIndex}
			<!-- Leading browse tab as a flyout trigger while on a browse index page. -->
			<div class="relative flex flex-1">
				<button
					type="button"
					aria-haspopup="menu"
					aria-expanded={flyoutOpen}
					onclick={() => (flyoutOpen = !flyoutOpen)}
					class="flex flex-1 flex-col items-center gap-1 px-1 py-1 text-[9.5px] font-medium tracking-wide transition-colors {active
						? 'text-ink'
						: 'text-ink-4'}"
				>
					<Icon
						class="h-[21px] w-[21px] {!color && active ? 'text-teal-2' : ''}"
						style={color ? `color: ${color}` : undefined}
					/>
					{item.label}
				</button>

				{#if flyoutOpen}
					<!-- Caret: pinned under the tab icon (wrapper centre), independent of
					     the bubble's shifted position so it always points at the trigger.
					     Rendered before the bubble so the bubble paints over its upper half,
					     leaving only the downward tip. -->
					<div
						class="absolute bottom-full left-1/2 z-50 mb-2 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border-r border-b border-border bg-background"
					></div>
					<!-- Bubble flyout: colour-coded tags onto the sibling browse surfaces.
					     Its left edge is pinned just inside the screen (the trigger is the
					     leftmost tab), so the whole bubble stays visible and reads off-centre
					     from the caret. -->
					<div
						class="absolute bottom-full left-2 z-50 mb-3 flex flex-col gap-3 rounded-2xl bg-background p-3 shadow-lg"
						role="menu"
					>
						{#each flyout as d (d.href)}
							{@const DIcon = sections[d.key].icon}
							{@const tagColor = sections[d.key].color}
							<a
								href={d.href}
								role="menuitem"
								onclick={() => (flyoutOpen = false)}
								class="flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-xs font-medium tracking-wide whitespace-nowrap uppercase no-underline"
								style="color: {tagColor}; background: color-mix(in srgb, {tagColor} 12%, transparent); border-color: color-mix(in srgb, {tagColor} 32%, transparent);"
							>
								<DIcon class="h-4 w-4" />
								{d.label}
							</a>
						{/each}
					</div>
				{/if}
			</div>
		{:else}
			<a
				href={item.href}
				aria-current={active ? 'page' : undefined}
				class="flex flex-1 flex-col items-center gap-1 px-1 py-1 text-[9.5px] font-medium tracking-wide no-underline transition-colors {active
					? 'text-ink'
					: 'text-ink-4'}"
			>
				<Icon
					class="h-[21px] w-[21px] {!color && active ? 'text-teal-2' : ''}"
					style={color ? `color: ${color}` : undefined}
				/>
				{item.label}
			</a>
		{/if}
	{/each}
</nav>

<!-- Click-catcher: dismiss the flyout when tapping anywhere else. -->
{#if flyoutOpen}
	<button
		type="button"
		aria-label="Close menu"
		class="fixed inset-0 z-40 md:hidden"
		onclick={() => (flyoutOpen = false)}
	></button>
{/if}
