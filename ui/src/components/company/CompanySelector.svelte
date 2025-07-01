<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { onDestroy, createEventDispatcher } from 'svelte';
  import appState, { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('CompanySelector');
  const dispatch = createEventDispatcher<{
    companySelected: CompanyResponse;
    companyCleared: void;
  }>();

  // Local component state - much simplified
  let ticker = $state('');
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

    actions.setLoading('company', true);
    actions.setError('company', null);

    try {
      const apiUrl = `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}&auto_ingest=true`;
      const company = await fetchApi<CompanyResponse>(apiUrl);

      // Use state manager action for selection - handles all cascading automatically
      actions.selectCompany(company);
      dispatch('companySelected', company);

      logger.info(`Company found: ${company.name}`, { company });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      actions.setError('company', errorMessage);
      logger.error('Error searching company:', { error: errorMessage });
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

  function handleCompanyCleared() {
    actions.clearAll();
    dispatch('companyCleared');
    ticker = '';
    searchResults = [];
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
        const apiUrl = `${config.api.baseUrl}/companies/search?q=${encodeURIComponent(ticker)}`;
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
        logger.error('Error searching companies:', { error: errorMessage });
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

    listLoading = true;
    listError = null;

    try {
      const apiUrl = `${config.api.baseUrl}/companies/list?offset=${currentOffset}&limit=${COMPANIES_PER_PAGE}`;
      logger.info(`Fetching company list: ${apiUrl}`);

      const companies = await fetchApi<CompanyResponse[]>(apiUrl);

      // Append new companies to the existing list for pagination
      if (currentOffset === 0) {
        allCompanies = companies;
      } else {
        allCompanies = [...allCompanies, ...companies];
      }

      // Check if we received less than the expected number of companies
      hasMoreCompanies = companies.length === COMPANIES_PER_PAGE;
      logger.info(`Fetched ${companies.length} companies`, { companies });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching company list:', { error: errorMessage });
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
  class="company-selector card collapsible-component"
  class:has-selected={appState.selectedCompany !== null}
  class:is-collapsed={isSearchCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="collapsible-heading">Company Selector</h2>

  <div class="search-container">
    <input
      type="text"
      bind:value={ticker}
      placeholder="Enter a ticker symbol"
      oninput={handleInput}
      onblur={handleInputBlur}
      onkeydown={handleInputKeydown}
    />
    <button onclick={searchCompany} disabled={loading}>
      {loading ? 'Searching' : 'Search'}
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading...</p>
    </div>
  {/if}

  {#if error}
    <p class="error-message">Error: {error}</p>
  {/if}

  {#if appState.selectedCompany}
    <div class="company-details selected-item">
      <h3>
        {appState.selectedCompany.name} ({appState.selectedCompany.tickers?.join(', ') || ''})
      </h3>
      <p>CIK: {appState.selectedCompany.cik}</p>
      <button onclick={handleCompanyCleared}>Clear Selection</button>
    </div>
  {/if}

  <!-- Move dropdown outside of collapsible container -->
  {#if showDropdown && searchResults.length > 0}
    <div
      class="search-results-dropdown"
      onmousedown={cancelBlur}
      ontouchstart={cancelBlur}
      role="listbox"
      aria-label="Company search results"
      tabindex="0"
    >
      {#each searchResults as company, index (company.id)}
        <!-- Using button instead of div for better accessibility -->
        <button
          type="button"
          class="search-result-item {currentFocusIndex === index ? 'search-result-focused' : ''}"
          onclick={() => selectCompanyFromDropdown(company)}
          onkeydown={(e) => handleKeydown(e, company)}
          role="option"
          aria-selected={appState.selectedCompany === company || currentFocusIndex === index}
        >
          <div class="company-name">{company.name}</div>
          <div class="company-ticker">{company.tickers?.join(', ') || ''}</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Company list section -->
  {#if showCompanyList}
    <div class="company-list-container">
      <h3 class="company-list-header">Browse All Companies</h3>

      {#if listLoading && allCompanies.length === 0}
        <div class="loading-container">
          <div class="loading-spinner"></div>
          <p>Loading companies...</p>
        </div>
      {:else if listError}
        <p class="error-message">Error loading companies: {listError}</p>
      {:else if allCompanies.length === 0}
        <p>No companies found.</p>
      {:else}
        <div class="company-list-scrollable">
          <ul class="company-list">
            {#each allCompanies as company (company.id)}
              <li class="company-list-item">
                <div class="company-info">
                  <div class="company-name">{company.name}</div>
                  <div class="company-ticker">{company.tickers?.join(', ') || ''}</div>
                </div>
                <button
                  class="select-company-button"
                  onclick={() => selectCompanyFromDropdown(company)}
                >
                  Select
                </button>
              </li>
            {/each}
          </ul>

          {#if hasMoreCompanies}
            <div class="load-more-container">
              <button class="load-more-button" onclick={handleLoadMore} disabled={listLoading}>
                {listLoading ? 'Loading...' : 'Load more companies'}
              </button>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .company-selector {
    /* Position is needed for dropdown, min-height handled by utility class */
    position: relative;
  }

  .search-container {
    display: flex;
    gap: var(--space-sm);
    position: relative; /* Ensure proper positioning context */
  }

  input {
    width: 100%;
    padding: var(--space-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    background-color: var(--color-input-background);
    transition:
      background-color 0.2s ease,
      color 0.2s ease;
  }

  button {
    padding: var(--space-sm) var(--space-md);
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  button:hover {
    background-color: var(--color-primary-hover);
  }

  button:disabled {
    background-color: var(--color-text-light);
    cursor: not-allowed;
  }

  .company-details {
    /* margin-top: var(--space-sm); */
    padding: var(--space-md); /* Consistent padding with other selectors */
  }

  .company-details.selected-item {
    cursor: default;
    margin-bottom: var(--space-sm);
    padding: var(--space-md); /* Ensure consistent padding */
  }

  .company-details h3 {
    margin: 0 0 var(--space-xs) 0;
    color: var(--color-text);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .company-details p {
    margin: var(--space-xs) 0 0 0;
    font-size: 0.9rem;
  }

  /* Add margin for the button */
  .company-details.selected-item p {
    margin-bottom: 0;
  }

  /* Search results dropdown */
  .search-results-dropdown {
    position: absolute;
    width: 100%;
    max-height: 300px;
    overflow-y: auto;
    background-color: var(--color-background, white);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    margin-top: 2px;
    z-index: 1000; /* Very high z-index */
    top: 66%;
    left: 0;
  }

  /* Ensure dropdown is always interactive regardless of parent state */
  .search-results-dropdown {
    pointer-events: auto !important;
  }

  .search-result-item {
    display: block;
    width: 100%;
    padding: var(--space-sm);
    cursor: pointer;
    border-bottom: 1px solid var(--color-border-light, #eee);
    background: none;
    border-left: none;
    border-right: none;
    border-top: none;
    text-align: left;
    font-family: inherit;
  }

  .search-result-item:hover,
  .search-result-item:focus {
    background-color: var(--color-border, --color-primary-hover);
    outline: none;
  }

  /* Style for keyboard navigation focused item */
  .search-result-focused {
    background-color: var(--color-border, --color-primary-hover) !important;
    border-left: 3px solid var(--color-primary);
  }

  .company-name {
    font-weight: 500;
    color: var(--color-primary);
  }

  .company-ticker {
    font-size: 0.9em;
    color: var(--color-text-light);
  }

  /* Add visual indicator for collapsed state */
  .company-selector.has-selected:after {
    opacity: 1;
  }

  /* Company list styles */
  .company-list-container {
    margin-top: var(--space-md);
    padding: var(--space-md);
    border-top: 1px solid var(--color-border);
  }

  .company-list-header {
    font-size: 1.2rem;
    font-weight: 500;
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
  }

  .company-list-scrollable {
    max-height: 400px;
    overflow-y: auto;
    padding-right: calc(var(--space-md) + 1rem); /* Add padding for scrollbar */
  }

  .company-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .company-list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm) 0;
    border-bottom: 1px solid var(--color-border-light, #eee);
  }

  .company-info {
    flex: 1;
  }

  .select-company-button {
    padding: var(--space-sm) var(--space-md);
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .select-company-button:hover {
    background-color: var(--color-primary-hover);
  }

  .load-more-button {
    display: block;
    width: 100%;
    padding: var(--space-sm);
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    text-align: center;
    transition: background-color 0.2s ease;
    margin-top: var(--space-md);
  }

  .load-more-button:hover {
    background-color: var(--color-primary-hover);
  }
</style>
