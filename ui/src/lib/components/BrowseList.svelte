<script lang="ts" generics="T">
	import { onMount, onDestroy } from 'svelte';
	import type { Snippet } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import { mobileTabBar } from '$lib/state/mobileTabBar.svelte';

	interface Props {
		/** Fetch one page of results. `search` is already trimmed (may be empty). */
		fetchPage: (
			skip: number,
			limit: number,
			search: string
		) => Promise<{ items: T[]; total: number }>;
		/** Renders one result row. */
		row: Snippet<[T]>;
		/** Renders one skeleton placeholder row during the initial load. */
		skeleton: Snippet;
		/** Eyebrow label for the non-search state, e.g. "All filings". */
		allLabel: string;
		/** Search input placeholder. */
		searchPlaceholder: string;
		/** Message shown when a query returns nothing. */
		emptyLabel?: string;
		pageSize?: number;
	}

	let {
		fetchPage,
		row,
		skeleton,
		allLabel,
		searchPlaceholder,
		emptyLabel = 'Nothing found.',
		pageSize = 30
	}: Props = $props();

	// Hide the bottom mobile nav while the search box is focused so it doesn't
	// crowd the on-screen keyboard; always restore it when leaving the page.
	onDestroy(() => (mobileTabBar.hidden = false));

	let total = $state(0);
	let items = $state<T[]>([]);
	let currentPage = $state(0);
	let loading = $state(true);
	let searchTerm = $state('');
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	let isSearching = $state(false);

	async function loadPage(p: number) {
		loading = true;
		try {
			const result = await fetchPage(p * pageSize, pageSize, searchTerm.trim());
			items = result.items;
			total = result.total;
			currentPage = p;
		} catch (e) {
			console.error('Failed to load list:', e);
		} finally {
			loading = false;
		}
	}

	function runSearch() {
		isSearching = true;
		loadPage(0).finally(() => (isSearching = false));
	}

	function handleSearchInput() {
		if (searchTimeout) clearTimeout(searchTimeout);
		searchTimeout = setTimeout(runSearch, 300);
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			if (searchTimeout) clearTimeout(searchTimeout);
			runSearch();
		}
	}

	const totalPages = $derived(Math.ceil(total / pageSize));

	onMount(() => loadPage(0));
</script>

<section>
	<SectionHead
		sticky
		eyebrow="{searchTerm.trim() ? 'Search results: ' + searchTerm : allLabel}{total > 0
			? ' · ' + total.toLocaleString() + ' results'
			: ''}"
		heading=""
	/>

	<!-- Search input -->
	<div
		class="mb-4 flex w-full items-center gap-2 rounded-lg border border-rule-2 bg-paper p-4 md:w-[340px]"
	>
		<Search class="h-3.5 w-3.5 shrink-0 text-ink-4" />
		<input
			type="text"
			bind:value={searchTerm}
			oninput={handleSearchInput}
			onkeydown={handleSearchKeydown}
			onfocus={() => (mobileTabBar.hidden = true)}
			onblur={() => (mobileTabBar.hidden = false)}
			placeholder={searchPlaceholder}
			class="min-w-0 flex-1 border-none bg-transparent p-0 text-sm text-ink outline-none"
		/>
		{#if isSearching}
			<span class="text-xs text-ink-4">...</span>
		{/if}
	</div>

	{#if loading && items.length === 0}
		<div>
			{#each Array(pageSize) as _, i (i)}
				{@render skeleton()}
			{/each}
		</div>
	{:else if items.length === 0}
		<p class="py-8 text-center text-sm text-ink-3">{emptyLabel}</p>
	{:else}
		<div class="transition-opacity duration-150" style="opacity: {loading ? 0.6 : 1};">
			{#each items as item (item)}
				{@render row(item)}
			{/each}
		</div>

		{#if totalPages > 1}
			<div class="mt-6 flex items-center justify-between pb-3">
				<button
					class="bg-transparent p-0 text-xs {currentPage > 0
						? 'cursor-pointer text-teal-2'
						: 'text-ink-4'}"
					disabled={currentPage === 0}
					onclick={() => loadPage(currentPage - 1)}
				>
					&larr; Previous
				</button>
				<span class="text-xs text-ink-4">Page {currentPage + 1} of {totalPages}</span>
				<button
					class="bg-transparent p-0 text-xs {currentPage < totalPages - 1
						? 'cursor-pointer text-teal-2'
						: 'text-ink-4'}"
					disabled={currentPage >= totalPages - 1}
					onclick={() => loadPage(currentPage + 1)}
				>
					Next &rarr;
				</button>
			</div>
		{/if}
	{/if}
</section>
