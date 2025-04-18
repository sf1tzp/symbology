<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

  // Using Svelte 5 runes
  let ticker = $state('');
  let selectedCompany = $state<CompanyResponse | null>(null);
  let loading = $state(false);
  let ingesting = $state(false);
  let error = $state<string | null>(null);
  let fetchStartTime = $state<number | null>(null);
  let loadingMessage = $state<string>('Searching...');
  // Flag to control when to show the loading spinner to avoid layout jumps
  let showLoadingSpinner = $state(false);
  // Flag to control when to update the button text
  let showLoadingText = $state(false);

  // New states for search results and dropdown
  let searchResults = $state<CompanyResponse[]>([]);
  let showDropdown = $state(false);
  let searchTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
  let blurTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
  // Timeout for showing the spinner
  let spinnerTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
  // For keyboard navigation
  let currentFocusIndex = $state(-1);
  // For tracking the loading message update interval
  let loadingMessageInterval = $state<ReturnType<typeof setInterval> | null>(null);

  onDestroy(() => {
    // Clear all timeouts and intervals
    if (searchTimeout) clearTimeout(searchTimeout);
    if (blurTimeout) clearTimeout(blurTimeout);
    if (spinnerTimeout) clearTimeout(spinnerTimeout);
    if (loadingMessageInterval) clearInterval(loadingMessageInterval);
  });

  const dispatch = createEventDispatcher<{
    companySelected: CompanyResponse;
    companyCleared: void;
  }>();
  const logger = getLogger('CompanySelector');

  // Function to start updating loading message during long operations
  function startLoadingMessageUpdates() {
    // Clear any existing interval first
    stopLoadingMessageUpdates();

    // Update once immediately
    updateLoadingMessage();

    // Then set up interval for subsequent updates
    loadingMessageInterval = setInterval(updateLoadingMessage, 1000);
  }

  // Function to stop the loading message updates
  function stopLoadingMessageUpdates() {
    if (loadingMessageInterval) {
      clearInterval(loadingMessageInterval);
      loadingMessageInterval = null;
    }
  }

  // Function to update loading message
  function updateLoadingMessage() {
    if (!loading || !fetchStartTime) {
      stopLoadingMessageUpdates();
      return;
    }

    const elapsedSeconds = Math.floor((Date.now() - fetchStartTime) / 1000);

    if (elapsedSeconds > 2) {
      loadingMessage = `Ingesting company data from EDGAR. This may take a minute... (${elapsedSeconds}s)`;
      ingesting = true;
    } else {
      loadingMessage = `Searching...`;
    }
  }

  /**
   * Unified search function that handles both real-time search and exact search
   * @param options Configuration options for the search
   */
  async function performSearch(options: {
    isExactSearch: boolean;
    debounceMs?: number;
    showSpinner?: boolean;
  }) {
    const { isExactSearch, debounceMs = 0, showSpinner = false } = options;

    // Clear previous timeouts
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    if (spinnerTimeout) {
      clearTimeout(spinnerTimeout);
    }

    // Validate input for exact search
    if (isExactSearch && !ticker) {
      error = 'Please enter a ticker symbol';
      return;
    }

    // Common reset logic for both modes
    if (!isExactSearch) {
      // For fuzzy search: reset spinner states immediately
      showLoadingSpinner = false;
      showLoadingText = false;

      // Clear selected company when typing for fuzzy search
      if (selectedCompany !== null) {
        logger.debug('[CompanySelector] Clearing selectedCompany due to typing', {
          previousCompany: selectedCompany,
        });
        selectedCompany = null;
        dispatch('companyCleared');
      }

      // If the input is empty or too short for fuzzy search, clear results
      if (!ticker || ticker.length < 2) {
        searchResults = [];
        showDropdown = false;
        return;
      }
    } else {
      // For exact search: prepare for potentially long operation
      ingesting = false;
      fetchStartTime = Date.now();
      loadingMessage = 'Searching...';
      selectedCompany = null;
      showDropdown = false;

      // Show spinner immediately for button clicks
      if (showSpinner) {
        showLoadingSpinner = true;
        showLoadingText = true;
      }
    }

    // Common reset logic
    error = null;

    // Define the search execution function
    const executeSearch = async () => {
      try {
        loading = true;

        // Start updating loading message for exact searches
        if (isExactSearch) {
          startLoadingMessageUpdates();
        }

        // Different API endpoints based on search type
        let apiUrl: string;
        let logContext: Record<string, any> = { ticker };

        if (isExactSearch) {
          apiUrl = `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}&auto_ingest=true`;
          logger.info(`Searching for company with ticker: ${ticker.toUpperCase()}`, { apiUrl });
        } else {
          apiUrl = `${config.api.baseUrl}/companies/search?query=${encodeURIComponent(ticker)}`;
          logger.info(`Searching for companies matching: ${ticker}`, { apiUrl });
        }

        // Execute the API call
        if (isExactSearch) {
          const company = await fetchApi<CompanyResponse>(apiUrl);
          selectedCompany = company;
          logger.info(`Company found: ${company.name}`, { company });
          dispatch('companySelected', company);
        } else {
          const results = await fetchApi<CompanyResponse[]>(apiUrl);
          searchResults = results;
          showDropdown = results.length > 0;
          logger.info(`Found ${results.length} matching companies`, { results });
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        logger.error(
          `Error ${isExactSearch ? 'searching company by ticker' : 'searching companies'}:`,
          {
            query: ticker,
            error: errorMessage,
          }
        );

        error = errorMessage;
        if (isExactSearch) {
          selectedCompany = null;
        }
      } finally {
        loading = false;

        if (isExactSearch) {
          ingesting = false;
          fetchStartTime = null;
          stopLoadingMessageUpdates();
        }

        // Clear spinner states
        if (spinnerTimeout) {
          clearTimeout(spinnerTimeout);
        }
        showLoadingSpinner = isExactSearch && showSpinner;
        showLoadingText = isExactSearch && showSpinner;
      }
    };

    // Either execute immediately or with debounce
    if (debounceMs > 0) {
      searchTimeout = setTimeout(executeSearch, debounceMs);
    } else {
      await executeSearch();
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

  // Function to select a company from the dropdown
  function selectCompanyFromDropdown(company: CompanyResponse) {
    selectedCompany = company;
    ticker = company.tickers && company.tickers.length > 0 ? company.tickers[0] : ''; // Safely access tickers
    showDropdown = false; // Hide the dropdown
    dispatch('companySelected', company);
  }

  // Handle keyboard navigation in dropdown
  function handleKeydown(event: KeyboardEvent, company: CompanyResponse) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectCompanyFromDropdown(company);
    }
  }

  // Handle input blur - hide dropdown with a small delay
  function handleBlur() {
    // Use a small timeout to allow for clicks on dropdown items
    // before hiding the dropdown
    blurTimeout = setTimeout(() => {
      showDropdown = false;
    }, 200);
  }

  // Function to cancel blur when interacting with dropdown
  function cancelBlur() {
    if (blurTimeout) {
      clearTimeout(blurTimeout);
    }
  }

  // Original function to search for a specific company by ticker (for exact match)
  function searchCompany() {
    performSearch({
      isExactSearch: true,
      debounceMs: 0, // No debounce for explicit search
      showSpinner: true,
    });
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
</script>

<div class="company-selector card">
  <h2>Company Selector</h2>

  <div class="search-container">
    <div class="search-input-wrapper">
      <input
        type="text"
        bind:value={ticker}
        placeholder="Enter a ticker symbol"
        oninput={handleInput}
        onblur={handleBlur}
        onkeydown={handleInputKeydown}
      />
      {#if showDropdown && searchResults.length > 0}
        <div
          class="search-results-dropdown"
          onmousedown={cancelBlur}
          ontouchstart={cancelBlur}
          role="listbox"
          aria-label="Company search results"
          tabindex="0"
        >
          {#each searchResults as company, index}
            <!-- Using button instead of div for better accessibility -->
            <button
              type="button"
              class="search-result-item {currentFocusIndex === index
                ? 'search-result-focused'
                : ''}"
              onclick={() => selectCompanyFromDropdown(company)}
              onkeydown={(e) => handleKeydown(e, company)}
              role="option"
              aria-selected={selectedCompany === company || currentFocusIndex === index}
            >
              <div class="company-name">{company.name}</div>
              <div class="company-ticker">{company.tickers?.join(', ') || ''}</div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
    <button onclick={searchCompany} disabled={loading}>
      {loading && showLoadingText ? 'Searching' : 'Search'}
    </button>
  </div>

  {#if loading && !showDropdown && showLoadingSpinner}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">{loadingMessage}</p>
    </div>
  {/if}

  {#if error}
    <p class="error">Error: {error}</p>
  {/if}

  {#if selectedCompany}
    <div class="company-details">
      <h3>{selectedCompany.name} ({selectedCompany.tickers?.join(', ') || ''})</h3>
    </div>
  {/if}
</div>

<style>
  .company-selector {
    margin-bottom: var(--space-md);
    /* Set a min-height to prevent layout shifts */
    min-height: 150px;
  }

  .search-container {
    display: flex;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
    position: relative; /* Ensure proper positioning context */
  }

  .search-input-wrapper {
    position: relative;
    flex: 1;
    z-index: 100; /* Increase z-index to ensure dropdown appears above everything */
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

  .error {
    color: var(--color-error);
  }

  .company-details {
    background-color: var(--color-surface);
    padding: var(--space-sm);
    border-radius: var(--border-radius);
    border-left: 4px solid var(--color-primary);
    margin-bottom: var(--space-md);
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: var(--space-md) 0;
  }

  .loading-spinner {
    border: 3px solid rgba(0, 0, 0, 0.1);
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border-left-color: var(--color-primary);
    animation: spin 1s linear infinite;
    margin-bottom: var(--space-sm);
    margin-top: var(--space-md);
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .loading-text {
    font-weight: 500;
    color: var(--color-text);
    margin-bottom: var(--space-sm);
  }

  /* New styles for dropdown */
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
    top: 100%;
    left: 0;
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
</style>
