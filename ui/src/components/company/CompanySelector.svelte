<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { onDestroy, createEventDispatcher } from 'svelte';
  import appState, { actions } from '$utils/state-manager.svelte';
  import { formatTitleCase } from '$src/utils/formatters';

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
    <input
      type="text"
      bind:value={ticker}
      placeholder={disclaimerAccepted ? 'Enter a ticker symbol' : 'Please accept disclaimer first'}
      oninput={handleInput}
      onblur={handleInputBlur}
      onkeydown={handleInputKeydown}
      disabled={!disclaimerAccepted}
      class="search-input"
    />
    <button
      onclick={searchCompany}
      disabled={loading || !disclaimerAccepted}
      class="btn btn-action"
    >
      {loading ? 'Searching' : 'Search'}
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner normal"></div>
      <p class="loading-message">Loading...</p>
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
          <button
            type="button"
            class="btn-item highlighted"
            onclick={() => selectCompanyFromDropdown(company)}
            onkeydown={(e) => handleKeydown(e, company)}
            role="option"
            aria-selected="true"
            disabled={!disclaimerAccepted}
          >
            <div class="company-name">{company.name}</div>
            <div class="meta">{company.tickers?.join(', ') || ''}</div>
          </button>
        {:else}
          <button
            type="button"
            class="btn-item"
            onclick={() => selectCompanyFromDropdown(company)}
            onkeydown={(e) => handleKeydown(e, company)}
            role="option"
            aria-selected="false"
            disabled={!disclaimerAccepted}
          >
            <div class="company-name">{company.name}</div>
            <div class="meta">{company.tickers?.join(', ') || ''}</div>
          </button>
        {/if}
      {/each}
    </div>
  {/if}

  <!-- Company list section -->
  {#if showCompanyList}
    <div class="section-container">
      <h3 class="section-title-small">Select a Company</h3>

      {#if listLoading && allCompanies.length === 0}
        <div class="loading-container">
          <div class="loading-spinner normal"></div>
          <p class="loading-message">Loading companies...</p>
        </div>
      {:else if listError}
        <p class="error-message">Error loading companies: {listError}</p>
      {:else if allCompanies.length === 0}
        <p class="no-content">No companies found.</p>
      {:else}
        <div class="company-list-scrollable">
          <div class="list-container">
            {#each allCompanies as company (company.id)}
              <div class="company-list-item">
                <div class="company-info">
                  <div class="company-name">{formatTitleCase(company.name)}</div>
                  <div class="meta">{company.tickers?.[0] || ''}</div>
                </div>
                <button
                  class="btn btn-action"
                  onclick={() => selectCompanyFromDropdown(company)}
                  disabled={!disclaimerAccepted}
                >
                  Select
                </button>
              </div>
            {/each}
          </div>

          {#if hasMoreCompanies}
            <div class="load-more-container">
              <button
                class="btn btn-action"
                onclick={handleLoadMore}
                disabled={listLoading || !disclaimerAccepted}
                style="width: 100%"
              >
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
  /* Custom input styling not covered by utilities */
  .search-input {
    width: 100%;
    padding: var(--space-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    background-color: var(--color-input-background);
    transition:
      background-color 0.2s ease,
      color 0.2s ease;
  }

  .search-input:disabled {
    background-color: var(--color-background);
    color: var(--color-text-light);
    cursor: not-allowed;
    opacity: 0.6;
  }

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
    opacity: 0.8;
  }
</style>
