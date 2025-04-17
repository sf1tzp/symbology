<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { FilingResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    filingSelected: FilingResponse;
  }>();
  const logger = getLogger('FilingsSelector');

  // Props
  const { companyId } = $props<{ companyId: string | undefined }>();

  // Using Svelte 5 runes
  let filings = $state<FilingResponse[]>([]);
  let selectedFiling = $state<FilingResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Watch for changes in companyId and fetch filings
  $effect(() => {
    if (companyId) {
      fetchFilings();
    } else {
      filings = [];
      selectedFiling = null;
    }
  });

  async function fetchFilings() {
    if (!companyId) {
      error = 'No company selected';
      return;
    }

    try {
      loading = true;
      error = null;
      filings = await fetchApi<FilingResponse[]>(
        `${config.api.baseUrl}/filings/by-company/${companyId}`
      );
      selectedFiling = null;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching filings:', err);
      filings = [];
    } finally {
      loading = false;
    }
  }

  function selectFiling(filing: FilingResponse) {
    selectedFiling = filing;
    dispatch('filingSelected', filing);
  }

  function handleKeyDown(event: KeyboardEvent, filing: FilingResponse) {
    // Select the filing when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectFiling(filing);
    }
  }
</script>

<div class="filings-selector card">
  <h2>Filings</h2>

  {#if !companyId}
    <p class="placeholder">Please select a company to view its filings</p>
  {:else if loading}
    <p>Loading filings...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if filings.length === 0}
    <p>No filings found for this company</p>
  {:else}
    <div class="filings-list scrollable" role="listbox" aria-label="Filings list">
      {#each filings as filing}
        <div
          class="filing-item {selectedFiling?.id === filing.id ? 'selected' : ''}"
          onclick={() => selectFiling(filing)}
          onkeydown={(e) => handleKeyDown(e, filing)}
          tabindex="0"
          role="option"
          aria-selected={selectedFiling?.id === filing.id}
        >
          <h3>
            {filing.filing_type}
            {#if filing.filing_url}
              <a
                href={filing.filing_url}
                target="_blank"
                rel="noopener noreferrer"
                class="source-link">view source</a
              >
            {/if}
          </h3>
          {#if filing.period_of_report}
            <p>
              Fiscal Year Ending: <strong
                >{new Date(filing.period_of_report).toLocaleDateString()}</strong
              >
            </p>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .filings-selector {
    margin-bottom: var(--space-md);
  }

  .placeholder {
    color: var(--color-text-light);
    font-style: italic;
  }

  .filings-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    margin-top: var(--space-md);
    max-height: 300px;
  }

  .filing-item {
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid var(--color-border);
  }

  .filing-item:hover {
    border-color: var(--color-primary);
  }

  .filing-item.selected {
    border-color: var(--color-primary);
    border-width: 2px;
    background-color: var(--color-surface);
  }

  .filing-item h3 {
    margin: 0 0 var(--space-xs) 0;
    color: var(--color-text);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filing-item p {
    margin: var(--space-xs) 0 0 0;
    font-size: 0.9rem;
  }

  .error {
    color: var(--color-error);
  }

  .source-link {
    font-size: 0.7rem;
    color: var(--color-primary);
    text-decoration: none;
  }

  .source-link:hover {
    text-decoration: underline;
  }
</style>
