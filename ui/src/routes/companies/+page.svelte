<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { ChevronRight } from '@lucide/svelte';
	import Search from '@lucide/svelte/icons/search';
	import type { CompanyListItem, CompanyListResponse } from '$lib/api-types';
	import { titleCase } from 'title-case';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	// Hide the bottom mobile nav while the search box is focused so it doesn't
	// crowd the on-screen keyboard; always restore it when leaving the page.
	onDestroy(() => (mobileTabBar.hidden = false));

	const PAGE_SIZE = 15;

	let total = $state(0);
	let companies = $state<CompanyListItem[]>([]);
	let _featured = $state<CompanyListItem[]>([]);
	let currentPage = $state(0);
	let loading = $state(true);
	let searchTerm = $state('');
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	let isSearching = $state(false);

	async function fetchCompanies(
		skip: number,
		limit: number,
		search?: string,
		sort?: string
	): Promise<CompanyListResponse> {
		const params = new SvelteURLSearchParams();
		params.set('skip', String(skip));
		params.set('limit', String(limit));
		if (search) params.set('search', search);
		if (sort) params.set('sort', sort);
		const res = await fetch(`/api/companies?${params}`);
		if (!res.ok) throw new Error('Failed to fetch companies');
		return res.json();
	}

	async function loadPage(page: number) {
		loading = true;
		try {
			const search = searchTerm.trim() || undefined;
			const result = await fetchCompanies(page * PAGE_SIZE, PAGE_SIZE, search);
			companies = result.companies;
			total = result.total;
			currentPage = page;
		} catch (e) {
			console.error('Failed to load companies:', e);
		} finally {
			loading = false;
		}
	}

	async function loadFeatured() {
		try {
			const result = await fetchCompanies(0, 3, undefined, 'recent');
			_featured = result.companies;
		} catch (e) {
			console.error('Failed to load featured:', e);
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
	const _showingFrom = $derived(currentPage * PAGE_SIZE + 1);
	const _showingTo = $derived(Math.min((currentPage + 1) * PAGE_SIZE, total));

	onMount(() => {
		loadPage(0);
		loadFeatured();
	});
</script>

<svelte:head>
	<title>Companies - Symbology</title>
	<meta name="description" content="Browse and explore public companies" />
</svelte:head>

<!-- Masthead -->
<!-- <section>
	<div class="flex-between flex-col items-stretch gap-6 md:flex-row md:items-end">
		<div>
			<SectionHead sticky stickyHeading eyebrow="symbology.online" heading="" />
			<h1 class="display" style="margin-bottom: 14px;">
				Browse
				{#if total > 0}
					<em>{total.toLocaleString()}</em>
				{/if}
				companies.
			</h1>
			<p class="lede" style="max-width: 52ch; color: var(--ink-2);">
				Filtered live across the SEC's public registrant universe. Click any company to land on its
				filing timeline and full analysis.
			</p>
		</div>

	</div>
</section> -->

<!-- Featured companies -->
<!-- {#if featured.length > 0 && !searchTerm.trim()}
	<section class="hairline-section" style="margin-top: 3rem;">
		<div class="flex-between" style="margin-bottom: 22px;">
			<h3 class="sub">Recently filed</h3>
		</div>
		<div class="grid-3">
			{#each featured as c (c.id)}
				<a
					href="/c/{c.ticker}"
					style="border: 1px solid var(--rule); border-radius: 8px; padding: 24px; text-decoration: none; color: inherit; display: block; transition: border-color 0.15s;"
					class="hover-card"
				>
					<div class="flex-between" style="margin-bottom: 18px;">
						<span class="tag" style="font-weight: 500; color: var(--ink);">{c.ticker}</span>
						{#if c.filing_count > 0}
							<span class="tag tag-new" style="font-size: 10px;">
								{c.filing_count} filings
							</span>
						{/if}
					</div>
					<div
						style="font-family: var(--serif); font-size: 22px; color: var(--ink); line-height: 1.25; margin-bottom: 6px;"
					>
						{titleCase((c.display_name || c.name).toLowerCase())}
					</div>
					<div class="meta" style="color: var(--ink-4); margin-bottom: 18px;">
						{c.sic_description || ''}
					</div>
					<div class="flex-between" style="padding-top: 14px; border-top: 1px solid var(--rule);">
						<span class="meta" style="color: var(--ink-3);">
							{#if c.last_filing_form && c.last_filing_date}
								{c.last_filing_form} &middot; {formatDate(c.last_filing_date)}
							{:else}
								No filings
							{/if}
						</span>
						<span style="font-size: 13px; color: var(--teal-2);">Open &rarr;</span>
					</div>
				</a>
			{/each}
		</div>
	</section>
{/if} -->

<!-- All companies table -->
<section class="">
	<SectionHead
		sticky
		eyebrow="{searchTerm.trim()
			? 'Search results: ' + searchTerm
			: 'All companies'} &middot; {total > 0 ? total.toLocaleString() + ' results' : ''}  results"
		heading=""
	/>
	<!-- <div class="flex-between" style="margin-bottom: 18px;">
		<h3 class="sub">
			{#if searchTerm.trim()}
				Search results
			{:else}
				All companies
			{/if}
		</h3>
		{#if total > 0}
			<span class="meta" style="color: var(--ink-4);">
				{total.toLocaleString()} results
			</span>
		{/if}
	</div> -->

	<!-- Search input -->
	<div
		class="mb-4 w-full p-4 md:w-[340px]"
		style="display: flex; align-items: center; gap: 8px;
			   border: 1px solid var(--rule-2); border-radius: 8px; background: var(--paper);"
	>
		<Search style="width: 14px; height: 14px; color: var(--ink-4); flex-shrink: 0;" />
		<input
			type="text"
			bind:value={searchTerm}
			oninput={handleSearchInput}
			onkeydown={handleSearchKeydown}
			onfocus={() => (mobileTabBar.hidden = true)}
			onblur={() => (mobileTabBar.hidden = false)}
			placeholder="Company name or ticker..."
			style="flex: 1; border: none; outline: none; background: transparent; font-family: var(--sans);
				   font-size: 14px; color: var(--ink); padding: 0;"
		/>
		{#if isSearching}
			<span class="meta" style="color: var(--ink-4);">...</span>
		{/if}
	</div>

	{#if loading && companies.length === 0}
		<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
			Loading...
		</p>
	{:else if companies.length === 0}
		<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
			No companies found.
		</p>
	{:else}
		<div style="opacity: {loading ? 0.6 : 1}; transition: opacity 0.15s;">
			{#each companies as c (c.id)}
				<a
					href="/c/{c.ticker}"
					class="docrow grid grid-cols-[45px_1fr_auto_auto_24px] text-inherit no-underline sm:grid-cols-[70px_1fr_auto_auto_24px]"
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
					</div>
					<div class="meta" style="color: var(--ink-3);">
						<!-- {#if c.last_filing_form && c.last_filing_date}
							{c.last_filing_form} &middot; {formatDate(c.last_filing_date)}
						{:else}
							<span style="color: var(--ink-4);">No filings</span>
						{/if} -->
					</div>
					<div class="meta" style="color: var(--ink-3); text-align: right;">
						<!-- {#if c.filing_count > 0}
							{c.filing_count} filings
						{/if} -->
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
	.hover-card:hover {
		border-color: var(--rule-2);
	}
</style>
