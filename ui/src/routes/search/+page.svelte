<script lang="ts">
	import { goto } from '$app/navigation';
	import SearchIcon from '@lucide/svelte/icons/search';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import type { PageData } from './$types';
	import type { SearchResultItem, SearchResponse } from '$lib/api-types';

	let { data }: { data: PageData } = $props();

	// Local state — NOT derived from data, so typing doesn't cause re-renders
	let searchInput = $state(data.query);
	let results = $state<SearchResultItem[]>(data.results);
	let total = $state(data.total);
	let searchOffset = $state(data.offset);
	let searchLimit = $state(data.limit);
	let loading = $state(false);
	let error = $state<string | undefined>(data.error);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let activeQuery = $state(data.query);

	// Filter state
	let showCompanies = $state(true);
	let showFilings = $state(true);
	let showAnalysis = $state(true);
	let formTypeFilter = $state(data.filters.formType || '');

	function buildApiUrl(query: string, offset: number = 0): string {
		const params = new SvelteURLSearchParams();
		params.set('q', query);
		params.set('limit', String(searchLimit));
		if (offset > 0) params.set('offset', String(offset));

		const entityTypes: string[] = [];
		if (showCompanies) entityTypes.push('company');
		if (showFilings) entityTypes.push('filing');
		if (showAnalysis) entityTypes.push('generated_content');
		if (entityTypes.length > 0 && entityTypes.length < 3) {
			entityTypes.forEach((t) => params.append('entity_types', t));
		}

		if (formTypeFilter) params.set('form_type', formTypeFilter);

		return `/api/search?${params}`;
	}

	function updateUrl(query: string) {
		const params = new SvelteURLSearchParams();
		if (query) params.set('q', query);
		const url = `/search${params.toString() ? '?' + params : ''}`;
		history.replaceState({}, '', url);
	}

	async function performSearch(query: string, offset: number = 0) {
		if (!query.trim()) {
			results = [];
			total = 0;
			activeQuery = '';
			error = undefined;
			updateUrl('');
			return;
		}

		loading = true;
		error = undefined;
		activeQuery = query;
		updateUrl(query);

		try {
			const res = await fetch(buildApiUrl(query, offset));
			if (!res.ok) throw new Error('Search failed');
			const data: SearchResponse = await res.json();
			results = data.results ?? [];
			total = data.total;
			searchOffset = offset;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Search failed';
			results = [];
			total = 0;
		} finally {
			loading = false;
		}
	}

	function handleInput() {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			performSearch(searchInput);
		}, 350);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			if (debounceTimer) clearTimeout(debounceTimer);
			performSearch(searchInput);
		}
	}

	function navigateToResult(result: SearchResultItem) {
		if (result.entity_type === 'company' && result.subtitle) {
			goto(`/c/${result.subtitle}`);
		} else if (result.entity_type === 'filing' && result.subtitle) {
			goto(`/f/${result.subtitle}`);
		} else if (result.entity_type === 'generated_content' && result.subtitle) {
			goto(`/c/${result.subtitle}`);
		}
	}

	function getEntityLabel(type: string): string {
		switch (type) {
			case 'company':
				return 'Company';
			case 'filing':
				return 'Filing';
			case 'generated_content':
				return 'Analysis';
			case 'company_group':
				return 'Group';
			default:
				return type;
		}
	}

	function getTagClass(type: string): string {
		switch (type) {
			case 'generated_content':
				return 'tag-new';
			default:
				return '';
		}
	}

	function formatDate(dateString: string | null | undefined): string {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	const currentPage = $derived(Math.floor(searchOffset / searchLimit) + 1);
	const totalPages = $derived(Math.ceil(total / searchLimit));

	function goToPage(pageNum: number) {
		const newOffset = (pageNum - 1) * searchLimit;
		performSearch(activeQuery, newOffset);
	}

	const formTypes = ['10-K', '10-Q', '8-K', 'DEF 14A', '20-F'];
</script>

<svelte:head>
	<title>{activeQuery ? `"${activeQuery}" - Search` : 'Search'} - Symbology</title>
	<meta name="description" content="Search companies, filings, and analyses" />
</svelte:head>

<!-- Masthead -->
<section>
	<div class="eyebrow" style="margin-bottom: 14px;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;SEARCH
	</div>
	<h1 class="display" style="font-size: clamp(2rem, 4vw, 3rem); margin-bottom: 28px;">
		Search across <em>everything</em>.
	</h1>

	<!-- Search input -->
	<div
		style="display: flex; align-items: center; gap: 10px; padding: 16px 22px;
		       border: 1px solid var(--rule-2); border-radius: 8px; background: var(--paper);"
	>
		<SearchIcon style="width: 18px; height: 18px; color: var(--ink-4); flex-shrink: 0;" />
		<input
			type="text"
			bind:value={searchInput}
			oninput={handleInput}
			onkeydown={handleKeydown}
			placeholder="Companies, filings, analyses..."
			style="flex: 1; border: none; outline: none; background: transparent; font-family: var(--sans);
			       font-size: 15px; color: var(--ink); padding: 0;"
		/>
		{#if loading}
			<span class="meta" style="color: var(--ink-4);">searching...</span>
		{:else}
			<span class="meta" style="color: var(--ink-4); white-space: nowrap;">&#8629; to search</span>
		{/if}
	</div>
</section>

<!-- Two-column: filters + results -->
<section
	style="margin-top: 3rem; display: grid; grid-template-columns: 240px 1fr; gap: 4rem; align-items: start;"
>
	<!-- Sidebar filters -->
	<aside style="position: sticky; top: 100px;">
		<h3 class="sub" style="margin-bottom: 18px;">Filters</h3>

		<!-- Entity type checkboxes -->
		<div class="meta" style="margin-bottom: 8px; color: var(--ink-3);">Entity type</div>
		<div style="display: flex; flex-direction: column; gap: 6px;">
			{#each [{ label: 'Companies', checked: showCompanies, toggle: () => {
						showCompanies = !showCompanies;
						if (activeQuery) performSearch(activeQuery);
					} }, { label: 'Filings', checked: showFilings, toggle: () => {
						showFilings = !showFilings;
						if (activeQuery) performSearch(activeQuery);
					} }, { label: 'Analyses', checked: showAnalysis, toggle: () => {
						showAnalysis = !showAnalysis;
						if (activeQuery) performSearch(activeQuery);
					} }] as filter (filter.label)}
				<label
					style="display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; font-size: 14px; color: {filter.checked
						? 'var(--ink)'
						: 'var(--ink-3)'};"
				>
					<input
						type="checkbox"
						checked={filter.checked}
						onchange={filter.toggle}
						style="display: none;"
					/>
					<span
						style="width: 14px; height: 14px; border-radius: 3px; border: 1.5px solid {filter.checked
							? 'var(--teal-2)'
							: 'var(--ink-4)'}; background: {filter.checked
							? 'var(--teal-2)'
							: 'transparent'}; display: inline-flex; align-items: center; justify-content: center;"
					>
						{#if filter.checked}
							<svg
								width="10"
								height="10"
								viewBox="0 0 24 24"
								fill="none"
								stroke="#fff"
								stroke-width="3.5"><path d="m5 12 5 5 9-9" /></svg
							>
						{/if}
					</span>
					{filter.label}
				</label>
			{/each}
		</div>

		<hr style="border: none; border-top: 1px solid var(--rule); margin: 24px 0;" />

		<!-- Form type tags -->
		<div class="meta" style="margin-bottom: 8px; color: var(--ink-3);">Form type</div>
		<div style="display: flex; flex-wrap: wrap; gap: 6px;">
			{#each formTypes as f (f)}
				<button
					class="tag"
					style="cursor: pointer; {formTypeFilter === f
						? 'background: var(--ink); color: var(--paper); border-color: var(--ink);'
						: ''}"
					onclick={() => {
						formTypeFilter = formTypeFilter === f ? '' : f;
						if (activeQuery) performSearch(activeQuery);
					}}
				>
					{f}
				</button>
			{/each}
		</div>
	</aside>

	<!-- Results -->
	<main class="min-w-5xl">
		{#if error}
			<div
				style="border-left: 3px solid var(--danger); padding: 1rem 1.25rem; background: color-mix(in oklch, var(--danger) 8%, var(--paper));"
			>
				<p class="meta" style="color: var(--danger);">Search error: {error}</p>
			</div>
		{:else if activeQuery && results.length === 0 && !loading}
			<div style="padding: 3rem 0; text-align: center;">
				<p class="body-text" style="color: var(--ink-3);">
					No results found for "{activeQuery}". Try a different query or adjust filters.
				</p>
			</div>
		{:else if results.length > 0}
			<div class="flex-between" style="margin-bottom: 28px;">
				<span class="meta" style="color: var(--ink-3);">
					{total} result{total === 1 ? '' : 's'} for
					<span style="color: var(--ink); font-family: var(--serif); font-style: italic;">
						"{activeQuery}"
					</span>
				</span>
			</div>

			<div style="opacity: {loading ? 0.5 : 1}; transition: opacity 0.15s;">
				{#each results as result (result.id)}
					<button
						onclick={() => navigateToResult(result)}
						style="display: block; width: 100%; text-align: left; text-decoration: none; padding: 20px 0;
						       border: none; background: none; border-bottom: 1px solid var(--rule); cursor: pointer; color: inherit;"
					>
						<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
							<span class="tag {getTagClass(result.entity_type)}" style="font-size: 11px;">
								{getEntityLabel(result.entity_type)}
							</span>
							{#if result.date_value}
								<span class="meta" style="color: var(--ink-4);">
									{formatDate(result.date_value)}
								</span>
							{/if}
							{#if result.subtitle}
								<span class="meta" style="color: var(--ink-4);">
									{result.subtitle}
								</span>
							{/if}
						</div>
						<div
							style="font-family: var(--serif); font-size: 22px; color: var(--ink);
							       letter-spacing: -0.015em; margin-bottom: 6px; line-height: 1.25;"
						>
							{result.title || 'Untitled'}
						</div>
						{#if result.headline}
							<div style="font-size: 14px; color: var(--ink-2); line-height: 1.55;">
								<!-- eslint-disable-next-line svelte/no-at-html-tags -->
								{@html result.headline}
							</div>
						{/if}
					</button>
				{/each}
			</div>

			<!-- Pagination -->
			{#if totalPages > 1}
				<div
					class="flex-between"
					style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--rule);"
				>
					<button
						class="meta"
						style="cursor: pointer; background: none; border: none; padding: 0; color: {currentPage >
						1
							? 'var(--teal-2)'
							: 'var(--ink-4)'};"
						disabled={currentPage <= 1}
						onclick={() => goToPage(currentPage - 1)}
					>
						&larr; Previous
					</button>
					<span class="meta" style="color: var(--ink-4);">
						Page {currentPage} of {totalPages}
					</span>
					<button
						class="meta"
						style="cursor: pointer; background: none; border: none; padding: 0; color: {currentPage <
						totalPages
							? 'var(--teal-2)'
							: 'var(--ink-4)'};"
						disabled={currentPage >= totalPages}
						onclick={() => goToPage(currentPage + 1)}
					>
						Next &rarr;
					</button>
				</div>
			{/if}
		{:else if !activeQuery}
			<!-- Empty state — shown inline in the results column -->
			<div class="mr-24 text-center">
				<SearchIcon
					style="width: 48px; height: 48px; color: var(--ink-4); margin: 0 auto 1.5rem;"
				/>
				<p class="section-heading" style="font-size: 1.5rem; margin-bottom: 0.5rem;">
					Enter a search query
				</p>
				<p class="body-text" style="color: var(--ink-3);">
					Search across companies, SEC filings, and AI-generated analyses
				</p>
			</div>
		{/if}
	</main>
</section>
