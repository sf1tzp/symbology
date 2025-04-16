<script lang="ts">
  import { onMount } from 'svelte';
  import { getLogger } from '$utils/logger';

  const logger = getLogger('FilingsSelector');

  let filings = [];
  let selectedFiling = null;
  let loading = false;
  let error = null;
  let selectedCompany = null;

  // Function declarations moved to module scope
  function handleCompanySelected(event) {
    selectedCompany = event.detail;
    selectedFiling = null;
    if (selectedCompany) {
      loadFilings(selectedCompany.id);
    } else {
      filings = [];
    }
  }

  async function loadFilings(companyId) {
    try {
      loading = true;
      filings = [];
      const response = await fetch(`/api/companies/${companyId}/filings`);
      if (!response.ok) throw new Error('Failed to fetch filings');
      filings = await response.json();
    } catch (err) {
      error = err.message;
      logger.error('Error fetching filings:', err);
    } finally {
      loading = false;
    }
  }

  function selectFiling(filing) {
    selectedFiling = filing;
    // Dispatch an event to notify parent components
    const event = new CustomEvent('filing-selected', { detail: filing });
    window.dispatchEvent(event);
  }

  // Listen for company selection events
  onMount(() => {
    window.addEventListener('company-selected', handleCompanySelected);
    return () => {
      window.removeEventListener('company-selected', handleCompanySelected);
    };
  });
</script>

/* eslint-disable no-inner-declarations */
<div class="filings-selector">
  <h2>Filings Selector</h2>

  {#if !selectedCompany}
    <p>Please select a company first</p>
  {:else if loading}
    <p>Loading filings...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if filings.length === 0}
    <p>No filings found for {selectedCompany.name}</p>
  {:else}
    <ul class="filings-list">
      {#each filings as filing}
        <li>
          <button
            class="filing-item {selectedFiling && selectedFiling.id === filing.id
              ? 'selected'
              : ''}"
            on:click={() => selectFiling(filing)}
            type="button"
          >
            <div class="filing-title">{filing.form_type}</div>
            <div class="filing-date">
              {new Date(filing.filing_date).toLocaleDateString()}
            </div>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .filings-selector {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .error {
    color: red;
  }

  .filings-list {
    max-height: 300px;
    overflow-y: auto;
    list-style: none;
    padding: 0;
    margin: 0;
  }

  li {
    margin-bottom: 0.25rem;
  }

  .filing-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.5rem;
    border: 1px solid #eee;
    border-radius: 4px;
    cursor: pointer;
    background-color: white;
  }

  .filing-item:hover {
    background-color: #f0f0f0;
  }

  .filing-item.selected {
    background-color: #e0e0e0;
    border-color: #aaa;
  }

  .filing-title {
    font-weight: bold;
  }

  .filing-date {
    font-size: 0.9rem;
    color: #666;
  }
</style>
