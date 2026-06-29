<script lang="ts">
	import { page } from '$app/state';
	import {
		buildMobileTabItems,
		buildContextNavItem,
		browseDestination,
		routeSection,
		siblingSections,
		isBrowseIndex,
		isCurrentPath,
		initials,
		type NavItem,
		type BrowseSection,
		type ContextKind,
		type NavUser
	} from '$lib/nav';
	import type { AmountBadge } from '$lib/supporter-plans';
	import Building2 from '@lucide/svelte/icons/building-2';
	import FileSearchCorner from '@lucide/svelte/icons/file-search-corner';
	import AudioWaveform from '@lucide/svelte/icons/audio-waveform';
	import Warehouse from '@lucide/svelte/icons/warehouse';
	import FileText from '@lucide/svelte/icons/file-text';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Heart from '@lucide/svelte/icons/heart';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';
	import { hints } from '$lib/state/hints.svelte';
	import X from '@lucide/svelte/icons/x';

	let { user = null, avatarBadge = null }: { user?: NavUser; avatarBadge?: AmountBadge | null } =
		$props();

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
		'/login': LogIn
	};

	// The browse section to surface in the leading tab. On a browse route it's
	// that route's section; on an off-surface page (FAQ / Support / Account) we
	// keep showing the section the viewer last visited so the tab doesn't snap
	// back to Companies. Remembered for the tab session in sessionStorage, synced
	// in an effect (client-only) so SSR and first client render agree from the
	// 'companies' default — no hydration mismatch — then it upgrades on mount.
	const SECTION_KEY = 'symbology:last-section';
	let remembered = $state<BrowseSection>('companies');
	$effect(() => {
		const here = routeSection(page.url.pathname);
		try {
			if (here) {
				remembered = here;
				sessionStorage.setItem(SECTION_KEY, here);
			} else {
				const stored = sessionStorage.getItem(SECTION_KEY);
				if (stored === 'companies' || stored === 'filings' || stored === 'synthesis') {
					remembered = stored;
				}
			}
		} catch {
			// sessionStorage can throw (private mode / disabled); stay in-memory.
			if (here) remembered = here;
		}
	});
	let section = $derived(routeSection(page.url.pathname) ?? remembered);
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

	// First-visit nudge: a one-time hint that the leading tab switches content
	// types, shown on the companies index (where new visitors land and the flyout
	// lives). Gated on hints.loaded so it never flashes before we've read the
	// dismissed flag. Opening the flyout or tapping its × turns hints off.
	$effect(() => {
		hints.load();
	});
	let showHint = $derived(
		hints.loaded && !hints.disabled && onBrowseIndex && section === 'companies' && !flyoutOpen
	);
	function toggleFlyout() {
		flyoutOpen = !flyoutOpen;
		if (flyoutOpen) hints.set(true);
	}
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
		<!-- Accent colour only when this tab is the current destination; an inactive
		     tab (incl. the section tab while on an off-surface page) reads muted. -->
		{@const color = active ? iconColor(item, isBrowseTab) : null}
		{#if isBrowseTab && onBrowseIndex}
			<!-- Leading browse tab as a flyout trigger while on a browse index page. -->
			<div class="relative flex flex-1">
				<button
					type="button"
					aria-haspopup="menu"
					aria-expanded={flyoutOpen}
					onclick={toggleFlyout}
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

				{#if showHint}
					<!-- One-time nudge toward the content-type switcher. Same translucent
					     blur + caret as the flyout, with a × that turns hints off for good
					     (re-enable in Settings). Non-modal: it doesn't trap taps elsewhere. -->
					<div
						class="absolute bottom-full left-1/2 z-40 mb-2 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border-r border-b border-border bg-background/95"
					></div>
					<div
						class="absolute bottom-full left-2 z-40 mb-3 flex w-max max-w-[70vw] items-center gap-2 rounded-2xl border border-border bg-background/95 py-2 pr-2 pl-3 shadow-sm"
						role="status"
					>
						<span class="text-xs text-ink-2">Tap here to switch content types</span>
						<button
							type="button"
							aria-label="Dismiss hint"
							onclick={() => hints.set(true)}
							class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-ink-4 transition-colors"
						>
							<X class="h-3.5 w-3.5" />
						</button>
					</div>
				{/if}

				{#if flyoutOpen}
					<!-- Caret: pinned under the tab icon (wrapper centre), independent of
					     the bubble's shifted position so it always points at the trigger.
					     Rendered before the bubble so the bubble paints over its upper half,
					     leaving only the downward tip. -->
					<div
						class="absolute bottom-full left-1/2 z-50 mb-2 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border-r border-b border-border bg-background/95"
					></div>
					<!-- Bubble flyout: colour-coded tags onto the sibling browse surfaces.
					     Its left edge is pinned just inside the screen (the trigger is the
					     leftmost tab), so the whole bubble stays visible and reads off-centre
					     from the caret. Translucent blur matches the navbar / section heads. -->
					<div
						class="absolute bottom-full left-2 z-50 mb-3 flex flex-col gap-3 rounded-2xl border border-border bg-background/95 p-3 shadow-sm"
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
								style="color: {tagColor}; background: color-mix(in srgb, {tagColor} 20%, var(--paper) 60%); border-color: color-mix(in srgb, {tagColor} 32%, transparent);"
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
				{#if item.href === '/a/watchlist' && user}
					<!-- Account tab carries the viewer's chosen profile icon — the earned
					     badge emoji, or their initials — mirroring the desktop navbar,
					     instead of a generic user glyph. -->
					<span
						class="flex h-[21px] w-[21px] items-center justify-center rounded-full bg-sage-2 font-mono font-semibold text-teal-2 {active
							? 'ring-1 ring-teal-2'
							: ''}"
					>
						{#if avatarBadge}
							<span class="text-[13px] leading-none">{avatarBadge.emoji}</span>
						{:else}
							<span class="text-[10px] leading-none">{initials(user.name)}</span>
						{/if}
					</span>
				{:else}
					<Icon
						class="h-[21px] w-[21px] {!color && active ? 'text-teal-2' : ''}"
						style={color ? `color: ${color}` : undefined}
					/>
				{/if}
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
