<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';

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

      const company = await fetchApi<CompanyResponse>(
        `${config.api.baseUrl}/companies/?ticker=${ticker.toUpperCase()}`
      );
      selectedCompany = company;

      // Dispatch event for other components
      const event = new CustomEvent('company-selected', { detail: company });
      window.dispatchEvent(event);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error searching company by ticker:', err);
      selectedCompany = null;
    } finally {
      loading = false;
    }
  }
</script>

<div class="company-selector">
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
      <h3>{selectedCompany.name}</h3>
      <p>Ticker: {selectedCompany.tickers}</p>
      <p>CIK: {selectedCompany.cik}</p>
    </div>
  {/if}
</div>

<style>
  .company-selector {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .search-container {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  input {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
  }

  button {
    padding: 0.5rem 1rem;
    background-color: #4285f4;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  button:hover {
    background-color: #3367d6;
  }

  button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }

  .error {
    color: red;
  }

  .company-details {
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f5f5f5;
    border-radius: 4px;
  }
</style>
