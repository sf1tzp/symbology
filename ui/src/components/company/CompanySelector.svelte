<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    companySelected: CompanyResponse;
  }>();
  const logger = getLogger('CompanySelector');

  // Using Svelte 5 runes
  let ticker = $state('');
  let selectedCompany = $state<CompanyResponse | null>(null);
  let loading = $state(false);
  let ingesting = $state(false);
  let error = $state<string | null>(null);
  let fetchStartTime = $state<number | null>(null);
  let loadingMessage = $state<string>('Searching...');

  // Function to update loading message during long operations
  function updateLoadingMessage() {
    if (!loading || !fetchStartTime) return;

    const elapsedSeconds = Math.floor((Date.now() - fetchStartTime) / 1000);

    if (elapsedSeconds > 2) {
      loadingMessage = `Ingesting company data from EDGAR. This may take a minute... (${elapsedSeconds}s)`;
      ingesting = true;
    } else if (elapsedSeconds > 1) {
      loadingMessage = `Still searching. We may need to retrieve data from EDGAR...`;
    } else {
      loadingMessage = `Searching (${elapsedSeconds}s)...`;
    }

    // Continue updating the message
    if (loading) {
      setTimeout(updateLoadingMessage, 1000);
    }
  }

  // Function to search for a company by ticker
  async function searchCompany() {
    if (!ticker) {
      error = 'Please enter a ticker symbol';
      return;
    }

    try {
      loading = true;
      ingesting = false;
      fetchStartTime = Date.now();
      loadingMessage = 'Searching...';
      error = null;
      selectedCompany = null;

      // Start updating the loading message
      updateLoadingMessage();

      const apiUrl = `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}`;
      logger.info(`Searching for company with ticker: ${ticker.toUpperCase()}`, { apiUrl });

      const company = await fetchApi<CompanyResponse>(apiUrl);
      selectedCompany = company;
      logger.info(`Company found: ${company.name}`, { company });

      // Dispatch event using Svelte's event system
      dispatch('companySelected', company);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('Error searching company by ticker:', {
        ticker: ticker.toUpperCase(),
        apiUrl: `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}`,
        error: errorMessage,
      });

      error = errorMessage;
      selectedCompany = null;
    } finally {
      loading = false;
      ingesting = false;
      fetchStartTime = null;
    }
  }
</script>

<div class="company-selector card">
  <h2>Company Selector</h2>

  <div class="search-container">
    <input
      type="text"
      bind:value={ticker}
      placeholder="Enter ticker symbol (e.g., AAPL)"
      onkeydown={(e) => e.key === 'Enter' && searchCompany()}
    />
    <button onclick={searchCompany} disabled={loading}>
      {loading ? 'Searching' : 'Search'}
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">{loadingMessage}</p>
      <!-- {#if ingesting} -->
      <!--   <p class="ingestion-notice"> -->
      <!--     We're retrieving and processing company data and filings from EDGAR. This process may take -->
      <!--     up to a minute for new companies. -->
      <!--   </p> -->
      <!-- {/if} -->
    </div>
  {/if}

  {#if error}
    <p class="error">Error: {error}</p>
  {/if}

  {#if selectedCompany}
    <div class="company-details">
      <h3>{selectedCompany.name} ({selectedCompany.tickers})</h3>
    </div>
  {/if}
</div>

<style>
  .company-selector {
    margin-bottom: var(--space-md);
  }

  .search-container {
    display: flex;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  input {
    flex: 1;
    padding: var(--space-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
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

  .ingestion-notice {
    font-size: 0.9em;
    background-color: var(--color-info-bg, #e1f5fe);
    color: var(--color-info-text, #0277bd);
    padding: var(--space-sm);
    border-radius: var(--border-radius);
    margin-top: var(--space-sm);
    text-align: center;
    max-width: 500px;
    border-left: 4px solid var(--color-info, #0277bd);
  }
</style>
