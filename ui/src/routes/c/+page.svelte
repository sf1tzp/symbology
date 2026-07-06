<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { ChevronRight, Sparkles, TrendingUp, SlidersHorizontal } from '@lucide/svelte';
	import Search from '@lucide/svelte/icons/search';
	import type {
		CompanyListItem,
		CompanyListResponse,
		CompanyFacetsResponse,
		IndustryFacet
	} from '$lib/api-types';
	import { titleCase } from 'title-case';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SegmentedControl from '$lib/components/SegmentedControl.svelte';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	// Hide the bottom mobile nav while the search box is focused so it doesn't
	// crowd the on-screen keyboard; always restore it when leaving the page.
	onDestroy(() => (mobileTabBar.hidden = false));

	const PAGE_SIZE = 30;

	type ContentFlag = '10k' | '10q' | 'diffs';
	type SortKey = 'ticker' | 'name' | 'recent';

	const SORT_OPTIONS = [
		{ value: 'ticker', label: 'Ticker' },
		{ value: 'name', label: 'Name' },
		{ value: 'recent', label: 'Recent' }
	];

	// Content-type filter chips — colors mirror the row content badges below.
	const CONTENT_OPTIONS: { flag: ContentFlag; label: string; color: string }[] = [
		{ flag: '10k', label: '10-K', color: 'var(--teal-2)' },
		{ flag: '10q', label: '10-Q', color: 'var(--plum)' },
		{ flag: 'diffs', label: 'Diffs', color: 'var(--warn)' }
	];

	let total = $state(0);
	let companies = $state<CompanyListItem[]>([]);
	let currentPage = $state(0);
	let loading = $state(true);
	let searchTerm = $state('');
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	let isSearching = $state(false);

	// Facet filter state.
	let sort = $state<SortKey>('ticker');
	let selectedSic = $state('');
	let contentFlags = $state<ContentFlag[]>([]);
	let industries = $state<IndustryFacet[]>([]);
	let showFilters = $state(false); // mobile filter panel

	async function fetchCompanies(skip: number, limit: number): Promise<CompanyListResponse> {
		const params = new SvelteURLSearchParams();
		params.set('skip', String(skip));
		params.set('limit', String(limit));
		const search = searchTerm.trim();
		if (search) params.set('search', search);
		if (sort !== 'ticker') params.set('sort', sort);
		if (selectedSic) params.set('sic', selectedSic);
		if (contentFlags.length) params.set('content', contentFlags.join(','));
		const res = await fetch(`/api/companies?${params}`);
		if (!res.ok) throw new Error('Failed to fetch companies');
		return res.json();
	}

	async function loadPage(page: number) {
		loading = true;
		try {
			const result = await fetchCompanies(page * PAGE_SIZE, PAGE_SIZE);
			companies = result.companies;
			total = result.total;
			currentPage = page;
		} catch (e) {
			console.error('Failed to load companies:', e);
		} finally {
			loading = false;
		}
	}

	async function loadFacets() {
		try {
			const res = await fetch('/api/companies/facets');
			if (!res.ok) return;
			const data: CompanyFacetsResponse = await res.json();
			industries = data.industries;
		} catch (e) {
			console.error('Failed to load facets:', e);
		}
	}

	function handleSearchInput() {
		if (searchTimeout) clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			isSearching = true;
			loadPage(0).finally(() => {
				isSearching = false;
			});
		}, 300);
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			if (searchTimeout) clearTimeout(searchTimeout);
			isSearching = true;
			loadPage(0).finally(() => {
				isSearching = false;
			});
		}
	}

	// Any facet change resets to the first page — the current page may not exist
	// in the newly-filtered result set.
	function onSort(v: string) {
		sort = v as SortKey;
		loadPage(0);
	}

	function toggleContent(flag: ContentFlag) {
		contentFlags = contentFlags.includes(flag)
			? contentFlags.filter((f) => f !== flag)
			: [...contentFlags, flag];
		loadPage(0);
	}

	function onIndustryChange() {
		loadPage(0);
	}

	function clearFilters() {
		selectedSic = '';
		contentFlags = [];
		sort = 'ticker';
		searchTerm = '';
		loadPage(0);
	}

	function _formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		try {
			const d = new Date(dateStr + 'T00:00:00');
			return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return dateStr;
		}
	}

	const totalPages = $derived(Math.ceil(total / PAGE_SIZE));
	// Non-search facet filters currently applied (drives the mobile badge + Clear).
	const activeFilterCount = $derived(
		(selectedSic ? 1 : 0) + contentFlags.length + (sort !== 'ticker' ? 1 : 0)
	);
	const hasAnyFilter = $derived(activeFilterCount > 0 || searchTerm.trim().length > 0);
	const selectedIndustryLabel = $derived(
		selectedSic ? (industries.find((i) => i.sic === selectedSic)?.sic_description ?? null) : null
	);
	const resultsScope = $derived(
		searchTerm.trim()
			? 'Search: ' + searchTerm.trim()
			: selectedIndustryLabel
				? titleCase(selectedIndustryLabel.toLowerCase())
				: 'All companies'
	);

	onMount(() => {
		loadPage(0);
		loadFacets();
	});
</script>

{#snippet badge(Icon: typeof Sparkles, label: string, color: string)}
	<span class="content-badge" style="--badge-color: {color};" aria-label={label}>
		<Icon size={11} strokeWidth={2} />
		<span class="badge-label">{label}</span>
	</span>
{/snippet}

{#snippet contentBadges(c: CompanyListItem)}
	{#if c.has_10k_page}
		{@render badge(Sparkles, '10-K', 'var(--teal-2)')}
	{/if}
	{#if c.has_10q_page}
		{@render badge(Sparkles, '10-Q', 'var(--plum)')}
	{/if}
	{#if c.has_diffs}
		{@render badge(TrendingUp, 'Diffs', 'var(--warn)')}
	{/if}
{/snippet}

<!-- Placeholder row matching the docrow grid, so first load reserves the same
     vertical space as the real list and avoids cumulative layout shift. -->
{#snippet skeletonRow()}
	<div
		class="docrow grid grid-cols-[45px_1fr_24px] items-center sm:grid-cols-[70px_1fr_auto_24px]"
		aria-hidden="true"
	>
		<div><span class="skel" style="width: 34px; height: 18px;"></span></div>
		<div>
			<span class="skel" style="width: 55%; height: 14px;"></span>
			<span class="skel" style="width: 38%; height: 11px; margin-top: 6px;"></span>
		</div>
		<div class="hidden sm:block">
			<span class="skel" style="width: 120px; height: 20px;"></span>
		</div>
		<span class="skel" style="width: 14px; height: 14px;"></span>
	</div>
{/snippet}

<svelte:head>
	<title>Companies - Symbology</title>
	<meta name="description" content="Browse and explore public companies" />
</svelte:head>

<!-- All companies table -->
<section class="">
	<SectionHead
		sticky
		eyebrow="{resultsScope} &middot; {total > 0 ? total.toLocaleString() + ' results' : ''}"
		heading=""
	/>

	<!-- Search + filter toolbar -->
	<div class="filter-bar">
		<div class="filter-top">
			<div class="search-box">
				<Search style="width: 14px; height: 14px; color: var(--ink-4); flex-shrink: 0;" />
				<input
					type="text"
					bind:value={searchTerm}
					oninput={handleSearchInput}
					onkeydown={handleSearchKeydown}
					onfocus={() => (mobileTabBar.hidden = true)}
					onblur={() => (mobileTabBar.hidden = false)}
					placeholder="Company name or ticker..."
				/>
				{#if isSearching}
					<span class="meta" style="color: var(--ink-4);">...</span>
				{/if}
			</div>

			<!-- Mobile: reveal the facet controls in a collapsible panel. -->
			<button
				type="button"
				class="filter-toggle sm:hidden"
				aria-expanded={showFilters}
				onclick={() => (showFilters = !showFilters)}
			>
				<SlidersHorizontal size={14} />
				Filters
				{#if activeFilterCount > 0}
					<span class="filter-count">{activeFilterCount}</span>
				{/if}
			</button>
		</div>

		<div class="filter-controls" class:open={showFilters}>
			<div class="filter-group">
				<span class="filter-label">Sort</span>
				<SegmentedControl
					options={SORT_OPTIONS}
					value={sort}
					onselect={onSort}
					ariaLabel="Sort companies"
				/>
			</div>

			<div class="filter-group">
				<span class="filter-label">Content</span>
				<div class="chips">
					{#each CONTENT_OPTIONS as opt (opt.flag)}
						{@const active = contentFlags.includes(opt.flag)}
						<button
							type="button"
							class="chip"
							class:active
							style="--chip-color: {opt.color};"
							aria-pressed={active}
							onclick={() => toggleContent(opt.flag)}
						>
							{opt.label}
						</button>
					{/each}
				</div>
			</div>

			<div class="filter-group">
				<span class="filter-label">Industry</span>
				<select
					class="industry-select"
					bind:value={selectedSic}
					onchange={onIndustryChange}
					aria-label="Filter by industry"
				>
					<option value="">All industries</option>
					{#each industries as ind (ind.sic + ind.sic_description)}
						<option value={ind.sic ?? ''}>
							{titleCase(ind.sic_description.toLowerCase())}
						</option>
					{/each}
				</select>
			</div>

			{#if hasAnyFilter}
				<button type="button" class="clear-filters" onclick={clearFilters}>Clear all</button>
			{/if}
		</div>
	</div>

	{#if loading && companies.length === 0}
		<div>
			{#each Array(PAGE_SIZE) as _, i (i)}
				{@render skeletonRow()}
			{/each}
		</div>
	{:else if companies.length === 0}
		<div class="empty">
			<p class="body-text" style="color: var(--ink-3);">
				No companies match{hasAnyFilter ? ' these filters' : ''}.
			</p>
			{#if hasAnyFilter}
				<button type="button" class="clear-filters" onclick={clearFilters}>Clear all filters</button
				>
			{/if}
		</div>
	{:else}
		<div style="opacity: {loading ? 0.6 : 1}; transition: opacity 0.15s;">
			{#each companies as c (c.id)}
				<a
					href="/c/{c.ticker}"
					class="docrow grid grid-cols-[45px_1fr_24px] items-center text-inherit no-underline sm:grid-cols-[70px_1fr_auto_24px]"
				>
					<div>
						<span class="tag" style="font-size: 11px; font-weight: 500; color: var(--ink);">
							{c.ticker}
						</span>
					</div>
					<div>
						<div style="font-size: 14px; font-weight: 500; color: var(--ink);">
							{titleCase((c.display_name || c.name).toLowerCase())}
						</div>
						{#if c.sic_description}
							<div
								class="font-mono text-xs text-ink-3"
								style="margin-top: 2px; color: var(--ink-4);"
							>
								{c.sic_description}
							</div>
						{/if}
						<!-- Badges wrap under the name on narrow screens; moved into their
						     own column from sm: up (see the .badges sm rule below). -->
						<div class="badges badges-compact flex sm:hidden">
							{@render contentBadges(c)}
						</div>
					</div>
					<div class="badges hidden sm:flex">
						{@render contentBadges(c)}
					</div>
					<ChevronRight style="width: 14px; height: 14px; color: var(--ink-4);" />
				</a>
			{/each}
		</div>

		<!-- Pagination -->
		{#if totalPages > 1}
			<div class="flex-between mt-6 pb-3">
				<button
					class="meta"
					style="cursor: pointer; background: none; border: none; padding: 0; color: {currentPage >
					0
						? 'var(--teal-2)'
						: 'var(--ink-4)'};"
					disabled={currentPage === 0}
					onclick={() => loadPage(currentPage - 1)}
				>
					&larr; Previous
				</button>
				<span class="meta" style="color: var(--ink-4);">
					Page {currentPage + 1} of {totalPages}
				</span>
				<button
					class="meta"
					style="cursor: pointer; background: none; border: none; padding: 0; color: {currentPage <
					totalPages - 1
						? 'var(--teal-2)'
						: 'var(--ink-4)'};"
					disabled={currentPage >= totalPages - 1}
					onclick={() => loadPage(currentPage + 1)}
				>
					Next &rarr;
				</button>
			</div>
		{/if}
	{/if}
</section>

<style>
	/* `display` is owned by the Tailwind utilities on each element (flex / hidden /
	   sm:flex / sm:hidden) — don't set it here, or the scoped class's higher
	   specificity overrides `hidden` and both badge copies render at once. */
	.badges {
		flex-wrap: wrap;
		gap: 6px;
	}

	.skel {
		display: inline-block;
		border-radius: 4px;
		background: var(--paper-2);
		animation: skel-pulse 1.4s ease-in-out infinite;
	}

	@keyframes skel-pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.45;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.skel {
			animation: none;
		}
	}

	/* --- Filter toolbar --- */
	.filter-bar {
		margin-bottom: 1.25rem;
	}

	.filter-top {
		display: flex;
		align-items: stretch;
		gap: 10px;
		margin-bottom: 14px;
	}

	.search-box {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
		padding: 0 12px;
		height: 44px;
		border: 1px solid var(--rule-2);
		border-radius: 8px;
		background: var(--paper);
	}
	.search-box input {
		flex: 1;
		border: none;
		outline: none;
		background: transparent;
		font-family: var(--sans);
		font-size: 14px;
		color: var(--ink);
		padding: 0;
	}

	.filter-toggle {
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
		padding: 0 14px;
		height: 44px;
		border: 1px solid var(--rule-2);
		border-radius: 8px;
		background: var(--paper);
		color: var(--ink-2);
		font-family: var(--sans);
		font-size: 13px;
		cursor: pointer;
	}
	/* `.sm:hidden` (Tailwind) toggles display; when visible it's inline-flex. */
	:global(.filter-toggle.sm\:hidden) {
		display: inline-flex;
	}
	@media (min-width: 640px) {
		:global(.filter-toggle.sm\:hidden) {
			display: none;
		}
	}

	.filter-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		border-radius: 999px;
		background: var(--teal-2);
		color: var(--paper);
		font-family: var(--mono);
		font-size: 11px;
		font-weight: 600;
	}

	/* Collapsed on mobile; the Filters button expands it. Always shown (and laid
	   out as a wrapping row) from sm: up. */
	.filter-controls {
		display: none;
		flex-direction: column;
		gap: 14px;
		padding-top: 4px;
	}
	.filter-controls.open {
		display: flex;
	}
	@media (min-width: 640px) {
		.filter-controls,
		.filter-controls.open {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			gap: 20px;
		}
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.filter-label {
		font-family: var(--mono);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-4);
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		padding: 4px 11px;
		border-radius: 999px;
		font-family: var(--sans);
		font-size: 12px;
		font-weight: 500;
		line-height: 1;
		white-space: nowrap;
		cursor: pointer;
		color: var(--ink-3);
		background: var(--paper);
		border: 1px solid var(--rule-2);
		transition:
			color 0.12s,
			background 0.12s,
			border-color 0.12s;
	}
	.chip:hover {
		color: var(--ink);
	}
	.chip.active {
		color: var(--chip-color);
		background: color-mix(in srgb, var(--chip-color) 12%, transparent);
		border-color: color-mix(in srgb, var(--chip-color) 40%, transparent);
	}

	.industry-select {
		max-width: 260px;
		padding: 6px 10px;
		border: 1px solid var(--rule-2);
		border-radius: 8px;
		background: var(--paper);
		font-family: var(--sans);
		font-size: 13px;
		color: var(--ink);
		cursor: pointer;
	}

	.clear-filters {
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		font-family: var(--mono);
		font-size: 11px;
		color: var(--ink-4);
		text-decoration: underline;
	}
	.clear-filters:hover {
		color: var(--ink-2);
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 2rem 0;
		text-align: center;
	}

	/* Mobile copy: icon-only pills to save horizontal room. */
	.badges-compact .badge-label {
		display: none;
	}
	.badges-compact .content-badge {
		padding: 4px;
	}

	/* Stacked under the company name on mobile. */
	:global(.badges.sm\:hidden) {
		margin-top: 6px;
	}

	.content-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 7px;
		border-radius: 999px;
		font-family: var(--sans);
		font-size: 11px;
		font-weight: 500;
		line-height: 1;
		white-space: nowrap;
		color: var(--badge-color);
		background: color-mix(in srgb, var(--badge-color) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--badge-color) 32%, transparent);
	}
</style>
