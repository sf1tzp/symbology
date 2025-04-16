<script lang="ts">
  import { onMount } from 'svelte';
  import { getLogger } from '$utils/logger';

  const logger = getLogger('CompanySelector');

  let companies = [];
  let selectedCompany = null;
  let loading = false;
  let error = null;

  // Function declaration moved to module scope
  function selectCompany(company) {
    selectedCompany = company;
    // Dispatch an event to notify parent components
    const event = new CustomEvent('company-selected', { detail: company });
    window.dispatchEvent(event);
  }

  // Fetch companies function moved out of onMount
  async function fetchCompanies() {
    try {
      loading = true;
      const response = await fetch('/api/companies');
      if (!response.ok) throw new Error('Failed to fetch companies');
      companies = await response.json();
    } catch (err) {
      error = err.message;
      logger.error('Error fetching companies:', err);
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchCompanies();
  });
</script>

/* eslint-disable no-inner-declarations */
<div class="company-selector">
  <h2>Company Selector</h2>

  {#if loading}
    <p>Loading companies...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if companies.length === 0}
    <p>No companies found</p>
  {:else}
    <select on:change={(e) => selectCompany(companies.find((c) => c.id === e.target.value))}>
      <option value="">Select a company</option>
      {#each companies as company}
        <option value={company.id}>{company.name} ({company.ticker})</option>
      {/each}
    </select>
  {/if}

  {#if selectedCompany}
    <div class="company-details">
      <h3>{selectedCompany.name}</h3>
      <p>Ticker: {selectedCompany.ticker}</p>
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

  .error {
    color: red;
  }

  select {
    width: 100%;
    padding: 0.5rem;
    margin-bottom: 1rem;
  }

  .company-details {
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f5f5f5;
    border-radius: 4px;
  }
</style>
