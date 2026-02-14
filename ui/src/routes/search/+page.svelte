<script lang="ts">
	import { goto } from '$app/navigation';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import Separator from '$lib/components/ui/separator/separator.svelte';
	import {
		Search,
		Building2,
		FileText,
		BrainCircuit,
		ChevronLeft,
		ChevronRight
	} from '@lucide/svelte';
	import type { PageData } from './$types';
	import type { SearchResultItem } from '$lib/api-types';

	let { data }: { data: PageData } = $props();

	let searchInput = $state(data.query);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Filter state
	let showCompanies = $state(
		data.filters.entityTypes.length === 0 || data.filters.entityTypes.includes('company')
	);
	let showFilings = $state(
		data.filters.entityTypes.length === 0 || data.filters.entityTypes.includes('filing')
	);
	let showAnalysis = $state(
		data.filters.entityTypes.length === 0 || data.filters.entityTypes.includes('generated_content')
	);
	let formTypeFilter = $state(data.filters.formType || '');
	let dateFromFilter = $state(data.filters.dateFrom || '');
	let dateToFilter = $state(data.filters.dateTo || '');

	function buildSearchUrl(query: string, offset: number = 0) {
		const params = new URLSearchParams();
		if (query) params.set('q', query);

		const entityTypes: string[] = [];
		if (showCompanies) entityTypes.push('company');
		if (showFilings) entityTypes.push('filing');
		if (showAnalysis) entityTypes.push('generated_content');

		// Only add entity_types if not all are selected
		if (entityTypes.length > 0 && entityTypes.length < 3) {
			entityTypes.forEach((t) => params.append('entity_types', t));
		}

		if (formTypeFilter) params.set('form_type', formTypeFilter);
		if (dateFromFilter) params.set('date_from', dateFromFilter);
		if (dateToFilter) params.set('date_to', dateToFilter);
		if (offset > 0) params.set('offset', offset.toString());

		return `/search?${params.toString()}`;
	}

	function performSearch() {
		if (!searchInput.trim()) return;
		goto(buildSearchUrl(searchInput));
	}

	function handleInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			if (debounceTimer) clearTimeout(debounceTimer);
			performSearch();
		}
	}

	function handleInput() {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			if (searchInput.trim()) {
				performSearch();
			}
		}, 500);
	}

	function applyFilters() {
		if (data.query) {
			goto(buildSearchUrl(data.query));
		}
	}

	function navigateToResult(result: SearchResultItem) {
		if (result.entity_type === 'company' && result.subtitle) {
			goto(`/c/${result.subtitle}`);
		} else if (result.entity_type === 'filing' && result.subtitle) {
			goto(`/f/${result.subtitle}`);
		} else if (result.entity_type === 'generated_content' && result.subtitle) {
			// subtitle is "TICKER" format, need to navigate with the result ID
			goto(`/c/${result.subtitle}`);
		}
	}

	function getEntityIcon(type: string) {
		switch (type) {
			case 'company':
				return Building2;
			case 'filing':
				return FileText;
			case 'generated_content':
				return BrainCircuit;
			default:
				return Search;
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
			default:
				return type;
		}
	}

	function getEntityVariant(type: string): 'default' | 'secondary' | 'outline' | 'destructive' {
		switch (type) {
			case 'company':
				return 'default';
			case 'filing':
				return 'secondary';
			case 'generated_content':
				return 'outline';
			default:
				return 'secondary';
		}
	}

	function formatDate(dateString: string | null | undefined): string {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	// Pagination
	$effect(() => {
		searchInput = data.query;
	});

	const currentPage = $derived(Math.floor(data.offset / data.limit) + 1);
	const totalPages = $derived(Math.ceil(data.total / data.limit));

	function goToPage(pageNum: number) {
		const newOffset = (pageNum - 1) * data.limit;
		goto(buildSearchUrl(data.query, newOffset));
	}
</script>

<svelte:head>
	<title>{data.query ? `"${data.query}" - Search` : 'Search'} - Symbology</title>
	<meta name="description" content="Search companies, filings, and analyses" />
</svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-bold">Search</h1>
		<p class="text-muted-foreground">Search across companies, filings, and generated analyses</p>
	</div>

	<!-- Search bar -->
	<div class="flex gap-2">
		<div class="relative flex-1">
			<Search class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				bind:value={searchInput}
				placeholder="Search companies, filings, analyses..."
				class="pl-10"
				oninput={handleInput}
				onkeydown={handleInputKeydown}
			/>
		</div>
		<Button onclick={performSearch} disabled={!searchInput.trim()}>Search</Button>
	</div>

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
		<!-- Filter sidebar -->
		<div class="space-y-6">
			<Card>
				<CardHeader>
					<CardTitle class="text-sm font-medium">Filters</CardTitle>
				</CardHeader>
				<CardContent class="space-y-4">
					<div class="space-y-3">
						<p class="text-sm font-medium">Entity Types</p>
						<label class="flex items-center space-x-2 text-sm">
							<input
								type="checkbox"
								bind:checked={showCompanies}
								onchange={applyFilters}
								class="rounded"
							/>
							<span>Companies</span>
						</label>
						<label class="flex items-center space-x-2 text-sm">
							<input
								type="checkbox"
								bind:checked={showFilings}
								onchange={applyFilters}
								class="rounded"
							/>
							<span>Filings</span>
						</label>
						<label class="flex items-center space-x-2 text-sm">
							<input
								type="checkbox"
								bind:checked={showAnalysis}
								onchange={applyFilters}
								class="rounded"
							/>
							<span>Analyses</span>
						</label>
					</div>

					<Separator />

					<div class="space-y-2">
						<label for="filter-form-type" class="text-sm font-medium">Form Type</label>
						<Input
							id="filter-form-type"
							bind:value={formTypeFilter}
							placeholder="e.g., 10-K, 10-Q"
							onchange={applyFilters}
						/>
					</div>

					<Separator />

					<div class="space-y-2">
						<p class="text-sm font-medium">Date Range</p>
						<div class="space-y-1">
							<label for="filter-date-from" class="text-xs text-muted-foreground">From</label>
							<Input
								id="filter-date-from"
								type="date"
								bind:value={dateFromFilter}
								onchange={applyFilters}
							/>
						</div>
						<div class="space-y-1">
							<label for="filter-date-to" class="text-xs text-muted-foreground">To</label>
							<Input
								id="filter-date-to"
								type="date"
								bind:value={dateToFilter}
								onchange={applyFilters}
							/>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>

		<!-- Results -->
		<div class="lg:col-span-3">
			{#if data.error}
				<div
					class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400"
				>
					Search error: {data.error}
				</div>
			{:else if data.query && data.results.length === 0}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<Search class="mb-4 h-12 w-12 text-muted-foreground" />
					<p class="text-lg font-medium">No results found</p>
					<p class="text-muted-foreground">Try adjusting your search terms or filters</p>
				</div>
			{:else if data.results.length > 0}
				<div class="space-y-2">
					<p class="text-sm text-muted-foreground">
						{data.total} result{data.total === 1 ? '' : 's'} for "{data.query}"
					</p>

					<div class="space-y-3">
						{#each data.results as result (result.id)}
							{@const Icon = getEntityIcon(result.entity_type)}
							<Card
								class="cursor-pointer transition-colors hover:bg-muted/50"
								onclick={() => navigateToResult(result)}
							>
								<CardContent class="py-4">
									<div class="flex items-start gap-3">
										<div class="mt-0.5 rounded-md bg-muted p-2">
											<Icon class="h-4 w-4 text-muted-foreground" />
										</div>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-2">
												<span class="font-medium">
													{result.title || 'Untitled'}
												</span>
												<Badge variant={getEntityVariant(result.entity_type)}>
													{getEntityLabel(result.entity_type)}
												</Badge>
												{#if result.subtitle}
													<span class="font-mono text-xs text-muted-foreground">
														{result.subtitle}
													</span>
												{/if}
											</div>
											{#if result.headline}
												<p class="mt-1 text-sm text-muted-foreground">
													{@html result.headline}
												</p>
											{/if}
											{#if result.date_value}
												<p class="mt-1 text-xs text-muted-foreground">
													{formatDate(result.date_value)}
												</p>
											{/if}
										</div>
									</div>
								</CardContent>
							</Card>
						{/each}
					</div>

					<!-- Pagination -->
					{#if totalPages > 1}
						<div class="flex items-center justify-center gap-2 pt-4">
							<Button
								variant="outline"
								size="sm"
								disabled={currentPage <= 1}
								onclick={() => goToPage(currentPage - 1)}
							>
								<ChevronLeft class="h-4 w-4" />
							</Button>
							<span class="text-sm text-muted-foreground">
								Page {currentPage} of {totalPages}
							</span>
							<Button
								variant="outline"
								size="sm"
								disabled={currentPage >= totalPages}
								onclick={() => goToPage(currentPage + 1)}
							>
								<ChevronRight class="h-4 w-4" />
							</Button>
						</div>
					{/if}
				</div>
			{:else if !data.query}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<Search class="mb-4 h-12 w-12 text-muted-foreground" />
					<p class="text-lg font-medium">Enter a search query</p>
					<p class="text-muted-foreground">
						Search across companies, SEC filings, and AI-generated analyses
					</p>
				</div>
			{/if}
		</div>
	</div>
</div>
