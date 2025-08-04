<script lang="ts">
  import { getComponentLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { onDestroy, createEventDispatcher } from 'svelte';
  import appState, { actions } from '$utils/state-manager.svelte';
  import { formatTitleCase } from '$src/utils/formatters';
  import { Button } from 'kampsy-ui';
  import { SearchInput } from 'kampsy-ui';
  import { Spinner } from 'kampsy-ui';

  const logger = getComponentLogger('CompanySelector');

  const dispatch = createEventDispatcher<{
    companySelected: CompanyResponse;
    companyCleared: void;
  }>();

  // Local component state - much simplified
  let ticker = $state('aapl');
  let searchResults = $state<CompanyResponse[]>([]);
  let showDropdown = $state(false);
  let allCompanies = $state<CompanyResponse[]>([]);
  let showCompanyList = $state(true);
  let isSearchCollapsed = $state(false);
  let currentFocusIndex = $state(-1);
  let listLoading = $state(false);
  let listError = $state<string | null>(null);
  let currentOffset = $state(0);
  let hasMoreCompanies = $state(true);

  // Constants
  const COMPANIES_PER_PAGE = 50;

  // Timeouts and intervals
  let searchTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
  let blurTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
  let hoverTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

  // Derived reactive state from the state manager (using $derived instead of $:)
  const loading = $derived(appState.loading.company);
  const error = $derived(appState.errors.company);
  const disclaimerAccepted = $derived(appState.disclaimerAccepted);

  // Auto-collapse when company is selected (using $effect instead of $:)
  $effect(() => {
    if (appState.selectedCompany) {
      isSearchCollapsed = true;
    }
  });

  onDestroy(() => {
    if (searchTimeout) clearTimeout(searchTimeout);
    if (blurTimeout) clearTimeout(blurTimeout);
    if (hoverTimeout) clearTimeout(hoverTimeout);
  });

  // Simplified search function using state manager actions
  async function searchCompany() {
    if (!ticker.trim()) {
      actions.setError('company', 'Please enter a ticker symbol');
      return;
    }

    logger.info('company_search_start', { ticker: ticker.trim().toUpperCase() });
    actions.setLoading('company', true);
    actions.setError('company', null);

    try {
      const apiUrl = `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}&auto_ingest=true`;
      const company = await fetchApi<CompanyResponse>(apiUrl);

      // Use state manager action for selection - handles all cascading automatically
      actions.selectCompany(company);
      dispatch('companySelected', company);

      logger.info('company_search_success', {
        ticker: ticker.toUpperCase(),
        companyId: company.id,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      actions.setError('company', errorMessage);
      logger.error('company_search_failed', {
        ticker: ticker.toUpperCase(),
        error: errorMessage,
      });
    } finally {
      actions.setLoading('company', false);
    }
  }

  function selectCompanyFromDropdown(company: CompanyResponse) {
    actions.selectCompany(company);
    dispatch('companySelected', company);
    ticker = company.tickers?.[0] || '';
    showDropdown = false;
  }

  // Functions to handle mouse events for expanding/collapsing the search UI
  function handleMouseEnter() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (isSearchCollapsed && appState.selectedCompany) {
      isSearchCollapsed = false;
    }
  }

  function handleMouseLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (appState.selectedCompany && !loading) {
      // Add a small delay before collapsing to prevent jumpy UI
      hoverTimeout = setTimeout(() => {
        isSearchCollapsed = true;
      }, 300);
    }
  }

  // Function to handle focus events for accessibility
  function handleFocus() {
    if (isSearchCollapsed && appState.selectedCompany) {
      isSearchCollapsed = false;
    }
  }

  // Function to search for companies as user types (with debounce)
  function handleInput() {
    performSearch({
      isExactSearch: false,
      debounceMs: 300, // 300ms debounce for typing
      showSpinner: false,
    });
  }

  // Function to cancel blur when interacting with dropdown
  function cancelBlur() {
    if (blurTimeout) {
      clearTimeout(blurTimeout);
    }
  }

  // Unified search function
  async function performSearch(options: {
    isExactSearch: boolean;
    debounceMs: number;
    showSpinner: boolean;
  }) {
    if (!ticker.trim()) {
      searchResults = [];
      showDropdown = false;
      return;
    }

    // Clear existing timeout
    if (searchTimeout) clearTimeout(searchTimeout);

    // Set up new search with debounce
    searchTimeout = setTimeout(async () => {
      if (options.showSpinner) {
        actions.setLoading('company', true);
      }

      try {
        const apiUrl = `${config.api.baseUrl}/companies/search?query=${encodeURIComponent(ticker)}`;
        const results = await fetchApi<CompanyResponse[]>(apiUrl);

        if (options.isExactSearch && results.length === 1) {
          // For exact search, select the company directly
          actions.selectCompany(results[0]);
          dispatch('companySelected', results[0]);
          showDropdown = false;
        } else {
          // For autocomplete, show dropdown
          searchResults = results;
          showDropdown = results.length > 0;
          currentFocusIndex = -1;
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        if (options.isExactSearch) {
          actions.setError('company', errorMessage);
        }
        logger.error('company_autocomplete_failed', { error: errorMessage });
        searchResults = [];
        showDropdown = false;
      } finally {
        if (options.showSpinner) {
          actions.setLoading('company', false);
        }
      }
    }, options.debounceMs);
  }

  // Function to handle keyboard events in dropdown items
  function handleKeydown(event: KeyboardEvent, company: CompanyResponse) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectCompanyFromDropdown(company);
    }
  }

  // Function to handle input blur with delay for dropdown interaction
  function handleInputBlur() {
    blurTimeout = setTimeout(() => {
      showDropdown = false;
      currentFocusIndex = -1;
    }, 150);
  }

  // Function to handle keyboard navigation in dropdown from the input field
  function handleInputKeydown(event: KeyboardEvent) {
    // Tab key for dropdown navigation when dropdown is open
    if (event.key === 'Tab' && showDropdown && searchResults.length > 0) {
      event.preventDefault(); // Prevent default tab behavior

      // Move to next item, or first item if none selected
      if (event.shiftKey) {
        // Shift+Tab: Move to previous item
        currentFocusIndex =
          currentFocusIndex <= 0 ? searchResults.length - 1 : currentFocusIndex - 1;
      } else {
        // Tab: Move to next item
        currentFocusIndex =
          currentFocusIndex >= searchResults.length - 1 ? 0 : currentFocusIndex + 1;
      }
    } else if (event.key === 'ArrowDown' && showDropdown && searchResults.length > 0) {
      // Arrow down also navigates the dropdown
      event.preventDefault();
      currentFocusIndex = currentFocusIndex >= searchResults.length - 1 ? 0 : currentFocusIndex + 1;
    } else if (event.key === 'ArrowUp' && showDropdown && searchResults.length > 0) {
      // Arrow up also navigates the dropdown
      event.preventDefault();
      currentFocusIndex = currentFocusIndex <= 0 ? searchResults.length - 1 : currentFocusIndex - 1;
    } else if (event.key === 'Escape' && showDropdown) {
      // Escape closes the dropdown
      showDropdown = false;
      currentFocusIndex = -1;
    } else if (event.key === 'Enter' && showDropdown && currentFocusIndex >= 0) {
      // Enter selects the currently focused item from dropdown
      event.preventDefault();
      selectCompanyFromDropdown(searchResults[currentFocusIndex]);
    } else if (event.key === 'Enter') {
      // Enter initiates search when there's no dropdown or nothing selected
      event.preventDefault();
      searchCompany();
    }
  }

  // Function to fetch the company list for browsing
  async function fetchCompanyList() {
    if (listLoading || !hasMoreCompanies) return;

    logger.info('company_list_start', {
      offset: currentOffset,
      limit: COMPANIES_PER_PAGE,
    });
    listLoading = true;
    listError = null;

    try {
      const apiUrl = `${config.api.baseUrl}/companies/list?offset=${currentOffset}&limit=${COMPANIES_PER_PAGE}`;

      const companies = await fetchApi<CompanyResponse[]>(apiUrl);

      // Append new companies to the existing list for pagination
      if (currentOffset === 0) {
        allCompanies = companies;
      } else {
        allCompanies = [...allCompanies, ...companies];
      }

      // Check if we received less than the expected number of companies
      hasMoreCompanies = companies.length === COMPANIES_PER_PAGE;

      logger.info('company_list_loaded', {
        companiesReceived: companies.length,
        totalCompanies: allCompanies.length,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('company_list_failed', {
        error: errorMessage,
        offset: currentOffset,
      });
      listError = errorMessage;
    } finally {
      listLoading = false;
    }
  }

  // Function to load more companies when scrolling to the bottom
  function handleLoadMore() {
    if (listLoading || !hasMoreCompanies) return;

    currentOffset += COMPANIES_PER_PAGE;
    fetchCompanyList();
  }

  // Initial fetch of the company list
  fetchCompanyList();
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="card content-container"
  class:has-selected={appState.selectedCompany !== null}
  class:is-collapsed={isSearchCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  {#if !disclaimerAccepted}
    <div class="content-box">
      <p class="meta">Please accept the disclaimer to search for companies.</p>
    </div>
  {/if}

  <div class="search-container">
    <SearchInput
      bind:value={ticker}
      placeholder={disclaimerAccepted ? 'Enter a ticker symbol' : 'Please accept disclaimer first'}
      oninput={handleInput}
      onblur={handleInputBlur}
      onkeydown={handleInputKeydown}
      disabled={!disclaimerAccepted}
    />
    <Button onclick={searchCompany} disabled={loading || !disclaimerAccepted} {loading}>
      {loading ? 'Searching' : 'Search'}
    </Button>
  </div>

  {#if loading}
    <div class="flex flex-col items-center p-8 gap-4">
      <Spinner size="medium" />
      <p class="text-[var(--color-text)] opacity-80 text-sm">Loading...</p>
    </div>
  {/if}

  {#if error}
    <p class="error-message">Error: {error}</p>
  {/if}

  <!-- Dropdown for search results -->
  {#if showDropdown && searchResults.length > 0}
    <div
      class="search-dropdown"
      onmousedown={cancelBlur}
      ontouchstart={cancelBlur}
      role="listbox"
      aria-label="Company search results"
      tabindex="0"
    >
      {#each searchResults as company, index (company.id)}
        {#if currentFocusIndex === index}
          <Button
            variant="secondary"
            size="medium"
            onclick={() => selectCompanyFromDropdown(company)}
            onkeydown={(e) => handleKeydown(e, company)}
            role="option"
            aria-selected="true"
            disabled={!disclaimerAccepted}
            class="w-full text-left bg-[var(--color-background)]"
          >
            <div class="company-name">{company.name}</div>
            <div class="meta">{company.tickers?.join(', ') || ''}</div>
          </Button>
        {:else}
          <Button
            variant="secondary"
            size="medium"
            onclick={() => selectCompanyFromDropdown(company)}
            onkeydown={(e) => handleKeydown(e, company)}
            role="option"
            aria-selected="false"
            disabled={!disclaimerAccepted}
            class="w-full text-left"
          >
            <div class="company-name">{company.name}</div>
            <div class="meta">{company.tickers?.join(', ') || ''}</div>
          </Button>
        {/if}
      {/each}
    </div>
  {/if}

  <!-- Company list section -->
  {#if showCompanyList}
    <div class="section-container company-list-section">
      <h3 class="section-title-small">Select a Company</h3>

      {#if listLoading && allCompanies.length === 0}
        <div class="flex flex-col items-center p-8 gap-4">
          <Spinner size="medium" />
          <p class="text-[var(--color-text)] opacity-80 text-sm">Loading companies...</p>
        </div>
      {:else if listError}
        <p class="error-message">Error loading companies: {listError}</p>
      {:else if allCompanies.length === 0}
        <p class="no-content">No companies found.</p>
      {:else}
        <div class="company-list-scrollable">
          <div class="list-container">
            <!-- sort by ticker -->
            {#each [...allCompanies].sort((a, b) => {
              const tickerA = a.tickers?.[0] || '';
              const tickerB = b.tickers?.[0] || '';
              return tickerA.localeCompare(tickerB);
            }) as company (company.id)}
              <div class="company-list-item">
                <div class="company-info">
                  <div class="company-name">{formatTitleCase(company.name)}</div>
                  <div class="meta">{company.tickers?.[0] || ''}</div>
                </div>
                <Button
                  size="small"
                  onclick={() => selectCompanyFromDropdown(company)}
                  disabled={!disclaimerAccepted}
                >
                  Select
                </Button>
              </div>
            {/each}
          </div>

          {#if hasMoreCompanies}
            <div class="load-more-container">
              <Button
                onclick={handleLoadMore}
                disabled={listLoading || !disclaimerAccepted}
                loading={listLoading}
                size="medium"
                class="w-full"
              >
                {listLoading ? 'Loading...' : 'Load more companies'}
              </Button>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  /* Search dropdown - positioned absolutely over other content */
  .search-dropdown {
    position: absolute;
    width: 100%;
    max-height: 300px;
    overflow-y: auto;
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    box-shadow: var(--hover-shadow);
    margin-top: 2px;
    z-index: 1000;
    top: 100%;
    left: 0;
  }

  .search-dropdown .btn-item {
    border: none;
    border-bottom: 1px solid var(--color-border);
    border-radius: 0;
  }

  .search-dropdown .btn-item:last-child {
    border-bottom: none;
  }

  /* Company name styling in dropdowns and lists */
  .company-name {
    font-weight: var(--font-weight-medium);
    color: var(--color-primary);
  }

  /* Improve contrast for meta text in this component */
  .meta {
    color: var(--color-text);
    opacity: 0.8;
  }

  /* Company list layout */
  .company-list-scrollable {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: var(--space-sm);
  }

  .company-list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm) 0;
    border-bottom: 1px solid var(--color-border);
  }

  .company-info {
    flex: 1;
  }

  .load-more-container {
    margin-top: var(--space-md);
  }

  /* Visual state indicators */
  .has-selected {
    border-color: var(--color-primary);
  }

  .is-collapsed {
    opacity: 0.9;
  }

  /* Mobile optimizations */
  @media (max-width: 768px) {
    .content-container {
      padding: var(--space-xs); /* Minimal internal padding */
    }

    .company-list-section {
      display: none; /* Hide the company list on mobile */
    }

    .search-container {
      gap: var(--space-xs); /* Reduce gap between input and button */
    }

    .btn-action {
      padding: var(--space-xs) var(--space-sm); /* Smaller button padding */
      font-size: 0.9rem; /* Smaller button text */
    }

    .search-dropdown {
      max-height: 200px; /* Smaller dropdown on mobile */
    }

    .loading-container {
      padding: var(--space-xs); /* Reduce loading container padding */
    }

    .loading-message {
      font-size: 0.85rem; /* Smaller loading text */
    }

    .error-message {
      font-size: 0.85rem; /* Smaller error text */
      padding: var(--space-xs); /* Less padding on error messages */
    }
  }
</style>
