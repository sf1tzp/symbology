<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Card, CardContent } from '$lib/components/ui/card';
	import type { CompanyResponse } from '$lib/generated-api-types';
	import { searchCompanies, getCompanies, handleApiError } from '$lib/api';
	import { RefreshCcw } from '@lucide/svelte';

	// Event dispatcher for parent components
	const dispatch = createEventDispatcher<{
		companySelected: CompanyResponse;
		companyCleared: void;
	}>();

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
				// Real API call to search companies
				const results = await searchCompanies(searchTerm, 10);

				searchResults = results;
				showDropdown = results.length > 0;
				currentFocusIndex = -1;
			} catch (error) {
				console.error('Search failed:', error);
				searchError = handleApiError(error);
				searchResults = [];
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
		const primaryTicker = company.tickers?.[0] || 'N/A';
		searchTerm = `${company.name} (${primaryTicker})`;
		showDropdown = false;
		dispatch('companySelected', company);

		// Navigate to company page if ticker is available
		if (company.tickers?.[0]) {
			goto(`/c/${company.tickers[0]}`);
		}
	}

	// Handle search button click
	function handleSearch() {
		if (searchResults.length === 1) {
			selectCompany(searchResults[0]);
		} else if (searchResults.length > 1) {
			// Show dropdown if multiple results
			showDropdown = true;
		} else {
			// Perform search if no results yet
			performSearch();
		}
	}

	// Handle keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		if (!showDropdown || searchResults.length === 0) {
			if (event.key === 'Enter') {
				event.preventDefault();
				handleSearch();
			}
			return;
		}

		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				currentFocusIndex =
					currentFocusIndex >= searchResults.length - 1 ? 0 : currentFocusIndex + 1;
				break;
			case 'ArrowUp':
				event.preventDefault();
				currentFocusIndex =
					currentFocusIndex <= 0 ? searchResults.length - 1 : currentFocusIndex - 1;
				break;
			case 'Enter':
				event.preventDefault();
				if (currentFocusIndex >= 0) {
					selectCompany(searchResults[currentFocusIndex]);
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
		if (searchResults.length > 0) {
			showDropdown = true;
		}
	}

	// Clear search
	function clearSearch() {
		searchTerm = '';
		searchResults = [];
		showDropdown = false;
		dispatch('companyCleared');
	}

	// Initialize component
	onMount(() => {
		loadFeaturedCompanies();
	});
</script>

<div class="company-selector relative" class:compact={variant === 'compact'}>
	<!-- Search Input -->
	<div class="flex space-x-2">
		<div class="relative flex-1">
			<Input
				bind:value={searchTerm}
				{placeholder}
				{disabled}
				oninput={handleInput}
				onkeydown={handleKeydown}
				onblur={handleBlur}
				onfocus={handleFocus}
				class="w-full"
			/>

			<!-- Clear button -->
			{#if searchTerm}
				<Button
					variant="ghost"
					size="sm"
					onclick={clearSearch}
					class="absolute top-1/2 right-2 h-6 w-6 -translate-y-1/2 p-0"
				>
					×
				</Button>
			{/if}

			<!-- Search Results Dropdown -->
			{#if showDropdown && searchResults.length > 0}
				<div class="absolute top-full right-0 left-0 z-50 mt-1">
					<Card class="border bg-popover shadow-lg">
						<CardContent class="p-0">
							<div class="max-h-60 overflow-y-auto">
								{#each searchResults as company, index}
									<button
										class="w-full border-b p-3 text-left transition-colors last:border-b-0 hover:bg-muted"
										class:bg-muted={currentFocusIndex === index}
										onclick={() => selectCompany(company)}
										type="button"
									>
										<div class="font-medium text-foreground">{company.name}</div>
										<div class="text-sm text-muted-foreground">
											{company.tickers?.join(', ') || 'No tickers'}
											{#if company.sic_description}
												• {company.sic_description}
											{/if}
										</div>
									</button>
								{/each}
							</div>
						</CardContent>
					</Card>
				</div>
			{/if}
		</div>

		<Button onclick={handleSearch} disabled={disabled || isSearching || !searchTerm.trim()}>
			{#if isSearching}
				Searching...
			{:else}
				Search
			{/if}
		</Button>
	</div>

	<!-- Error Message -->
	{#if searchError}
		<div class="mt-2 text-sm text-red-500">
			Error: {searchError}
		</div>
	{/if}

	<!-- Featured Companies List (only shown when showCompanyList is true) -->
	{#if showCompanyList && variant === 'default'}
		<div class="mt-6">
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
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				{#each featuredCompanies.slice(0, 8) as company}
					<Card class="cursor-pointer transition-shadow hover:shadow-md">
						<CardContent class="p-4">
							<div class="flex items-center justify-between">
								<div class="flex-1">
									<div class="text-sm font-medium">{company.name}</div>
									<div class="text-xs text-muted-foreground">
										{company.tickers?.[0] || 'N/A'}
										{#if company.sic_description}
											• {company.sic_description}
										{/if}
									</div>
								</div>
								<Button
									variant="outline"
									size="sm"
									onclick={() => selectCompany(company)}
									{disabled}
								>
									Select
								</Button>
							</div>
						</CardContent>
					</Card>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.company-selector.compact .grid {
		display: none;
	}
</style>
