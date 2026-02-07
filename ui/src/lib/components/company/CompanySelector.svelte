<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import type { CompanyResponse, SearchResultItem } from '$lib/api-types';
	import { searchCompanies, getCompanies, search, handleApiError } from '$lib/api';
	import { RefreshCcw } from '@lucide/svelte';
	import { titleCase } from 'title-case';

	// Props
	interface Props {
		placeholder?: string;
		showCompanyList?: boolean;
		variant?: 'default' | 'compact';
		disabled?: boolean;
	}

	let {
		placeholder = 'Enter company name or ticker (e.g., AAPL, Apple)',
		showCompanyList = true,
		variant = 'default',
		disabled = false
	}: Props = $props();

	// Component state
	let searchTerm = $state('');
	let searchResults = $state<CompanyResponse[]>([]);
	let unifiedResults = $state<SearchResultItem[]>([]);
	let useUnifiedSearch = $state(false);
	let showDropdown = $state(false);
	let isSearching = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	let currentFocusIndex = $state(-1);
	let searchError = $state<string | null>(null);

	// Featured companies - loaded from API on mount
	let featuredCompanies = $state<CompanyResponse[]>([]);
	let isShuffling = $state(false);

	// Load featured companies on mount
	async function loadFeaturedCompanies() {
		try {
			isShuffling = true;
			// Get up to 48 companies to pick from
			const companies = await getCompanies(0, 48);

			// Randomly select 8 companies from the available pool
			const shuffled = [...companies].sort(() => Math.random() - 0.5);
			featuredCompanies = shuffled.slice(0, 8);
		} catch (error) {
			console.error('Failed to load featured companies:', error);
			searchError = handleApiError(error);
		} finally {
			isShuffling = false;
		}
	}

	// Shuffle featured companies
	async function shuffleFeaturedCompanies() {
		await loadFeaturedCompanies();
	}

	// Search function with debounce
	async function performSearch() {
		if (!searchTerm.trim()) {
			searchResults = [];
			unifiedResults = [];
			useUnifiedSearch = false;
			showDropdown = false;
			searchError = null;
			return;
		}

		// Clear existing timeout
		if (searchTimeout) clearTimeout(searchTimeout);

		// Set up debounced search
		searchTimeout = setTimeout(async () => {
			isSearching = true;
			searchError = null;

			try {
				if (searchTerm.trim().length >= 3) {
					// Use unified search for longer queries
					const response = await search(searchTerm, { limit: 10 });
					unifiedResults = response.results ?? [];
					searchResults = [];
					useUnifiedSearch = true;
					showDropdown = unifiedResults.length > 0;
				} else {
					// Use company search for short queries (ticker prefixes)
					const results = await searchCompanies(searchTerm, 10);
					searchResults = results;
					unifiedResults = [];
					useUnifiedSearch = false;
					showDropdown = results.length > 0;
				}
				currentFocusIndex = -1;
			} catch (error) {
				console.error('Search failed:', error);
				searchError = handleApiError(error);
				searchResults = [];
				unifiedResults = [];
				showDropdown = false;
			} finally {
				isSearching = false;
			}
		}, 300);
	}

	// Handle input changes
	function handleInput() {
		performSearch();
	}

	// Handle company selection
	function selectCompany(company: CompanyResponse) {
		goto(`/c/${company.ticker}`);
	}

	// Handle unified search result selection
	function selectResult(result: SearchResultItem) {
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
			default:
				return type;
		}
	}

	// Get the active result list for keyboard navigation
	const activeResults = $derived(useUnifiedSearch ? unifiedResults : searchResults);

	// Handle search button click
	function handleSearch() {
		if (searchTerm.trim().length >= 3) {
			// Navigate to full search page for longer queries
			goto(`/search?q=${encodeURIComponent(searchTerm)}`);
			return;
		}
		if (searchResults.length === 1) {
			selectCompany(searchResults[0]);
		} else if (searchResults.length > 1) {
			showDropdown = true;
		} else {
			performSearch();
		}
	}

	// Handle keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		if (!showDropdown || activeResults.length === 0) {
			if (event.key === 'Enter') {
				handleSearch();
			}
			return;
		}

		switch (event.key) {
			case 'ArrowDown':
				currentFocusIndex =
					currentFocusIndex >= activeResults.length - 1 ? 0 : currentFocusIndex + 1;
				break;
			case 'ArrowUp':
				currentFocusIndex =
					currentFocusIndex <= 0 ? activeResults.length - 1 : currentFocusIndex - 1;
				break;
			case 'Enter':
				if (currentFocusIndex >= 0) {
					if (useUnifiedSearch) {
						selectResult(unifiedResults[currentFocusIndex]);
					} else {
						selectCompany(searchResults[currentFocusIndex]);
					}
				} else {
					handleSearch();
				}
				break;
			case 'Escape':
				showDropdown = false;
				currentFocusIndex = -1;
				break;
		}
	}

	// Handle input blur
	function handleBlur() {
		// Delay hiding dropdown to allow for clicks
		setTimeout(() => {
			showDropdown = false;
			currentFocusIndex = -1;
		}, 150);
	}

	// Handle input focus
	function handleFocus() {
		if (activeResults.length > 0) {
			showDropdown = true;
		}
	}

	// Initialize component
	onMount(() => {
		loadFeaturedCompanies();
	});
</script>

<!-- Search Input -->
<div class="flex space-x-4">
	<div class="relative flex-1">
		<Input
			bind:value={searchTerm}
			{placeholder}
			{disabled}
			oninput={handleInput}
			onkeydown={handleKeydown}
			onblur={handleBlur}
			onfocus={handleFocus}
			class=""
		/>
		<!-- Search Results Dropdown -->
		{#if showDropdown && activeResults.length > 0}
			<Card class="absolute top-full z-50 border border-white bg-popover shadow-lg">
				<CardContent class="p-0">
					<div class="max-h-60 overflow-y-auto">
						{#if useUnifiedSearch}
							{#each unifiedResults as result, index}
								<button
									class="w-full border-b p-2 text-left transition-colors last:border-b-0 hover:bg-muted"
									class:bg-muted={currentFocusIndex === index}
									onclick={() => selectResult(result)}
									type="button"
								>
									<div class="flex items-center gap-2">
										<span class="font-medium text-foreground">
											{result.title || 'Untitled'}
										</span>
										<Badge variant="outline" class="text-xs">
											{getEntityLabel(result.entity_type)}
										</Badge>
									</div>
									<div class="text-sm text-muted-foreground">
										{#if result.subtitle}{result.subtitle}{/if}
										{#if result.headline}
											<span class="ml-1">{@html result.headline}</span>
										{/if}
									</div>
								</button>
							{/each}
							{#if unifiedResults.length >= 10}
								<button
									class="w-full p-2 text-center text-sm text-muted-foreground transition-colors hover:bg-muted"
									onclick={() => goto(`/search?q=${encodeURIComponent(searchTerm)}`)}
									type="button"
								>
									View all results →
								</button>
							{/if}
						{:else}
							{#each searchResults as company, index}
								<button
									class="w-full border-b p-2 text-left transition-colors last:border-b-0 hover:bg-muted"
									class:bg-muted={currentFocusIndex === index}
									onclick={() => selectCompany(company)}
									type="button"
								>
									<div class="font-medium text-foreground">
										{titleCase(company.name.toLowerCase())}
									</div>
									<div class="text-sm text-muted-foreground">
										{company.ticker}
										{#if company.sic_description}
											• {company.sic_description}
										{/if}
									</div>
								</button>
							{/each}
						{/if}
					</div>
				</CardContent>
			</Card>
		{/if}
	</div>

	<Button
		onclick={handleSearch}
		hidden={showDropdown}
		disabled={disabled || isSearching || !searchTerm.trim()}
	>
		{#if isSearching}
			Searching...
		{:else}
			Search
		{/if}
	</Button>
</div>

{#if searchError}
	<div class="mt-4 text-sm text-red-500">
		Error: {searchError}
	</div>
{/if}

{#if showCompanyList}
	<div class="mt-8">
		<div class="mb-4 flex items-center justify-between">
			<h3 class="text-lg font-semibold">Popular Companies</h3>
			<Button
				variant="outline"
				size="sm"
				onclick={shuffleFeaturedCompanies}
				disabled={disabled || isShuffling}
				class="flex items-center gap-2"
			>
				<RefreshCcw class={isShuffling ? 'animate-spin' : ''} size={16} />
				{#if isShuffling}
					Shuffling...
				{:else}
					Shuffle
				{/if}
			</Button>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			{#each featuredCompanies.slice(0, 8) as company}
				<Card class="transition-shadow hover:shadow-md" onclick={() => selectCompany(company)}>
					<CardContent class="">
						<div class="flex justify-between">
							<div class="">
								<div class="font-medium">{titleCase(company.name.toLowerCase())}</div>
								<div class="text-xs text-muted-foreground">
									{company.ticker}
									{#if company.sic_description}
										• {company.sic_description}
									{/if}
								</div>
							</div>
							<Button variant="outline" size="sm" onclick={() => selectCompany(company)} {disabled}>
								Select
							</Button>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
{/if}
