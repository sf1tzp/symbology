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
  let error = $state<string | null>(null);

  // Function to search for a company by ticker
  async function searchCompany() {
    if (!ticker) {
      error = 'Please enter a ticker symbol';
      return;
    }

    try {
      loading = true;
      error = null;
      selectedCompany = null;

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
      {loading ? 'Searching...' : 'Search'}
    </button>
  </div>

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
</style>
