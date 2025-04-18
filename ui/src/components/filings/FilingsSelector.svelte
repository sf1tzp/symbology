<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { FilingResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

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

  // New state variable for collapsible behavior
  let isListCollapsed = $state(false);
  let hoverTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on destroy
  onDestroy(() => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
  });

  // Watch for changes in companyId and fetch filings
  $effect(() => {
    logger.debug('[FilingsSelector] Effect watching companyId triggered', { companyId });
    if (companyId) {
      fetchFilings();
    } else {
      logger.debug(
        '[FilingsSelector] Clearing filings and selectedFiling because companyId is undefined'
      );
      filings = [];
      selectedFiling = null;
      isListCollapsed = false; // Reset collapsed state when company changes
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

    // Collapse the filings list when a filing is selected
    if (filing) {
      isListCollapsed = true;
    }
  }

  // Functions to handle mouse events for expanding the list
  function handleMouseEnter() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (isListCollapsed && selectedFiling) {
      isListCollapsed = false;
    }
  }

  function handleMouseLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (selectedFiling && !loading) {
      // Add a small delay before collapsing to prevent jumpy UI
      hoverTimeout = setTimeout(() => {
        isListCollapsed = true;
      }, 300);
    }
  }

  // Function to handle focus events for accessibility
  function handleFocus() {
    if (isListCollapsed && selectedFiling) {
      isListCollapsed = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent, filing: FilingResponse) {
    // Select the filing when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectFiling(filing);
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="filings-selector card collapsible-component"
  class:has-selected={selectedFiling !== null}
  class:is-collapsed={isListCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="collapsible-heading" class:is-collapsed={isListCollapsed}>Filings</h2>

  {#if !companyId}
    <p class="placeholder">Please select a company to view its filings</p>
  {:else if loading}
    <p>Loading filings...</p>
  {:else if error}
    <p class="error-message">Error: {error}</p>
  {:else if filings.length === 0}
    <p>No filings found for this company</p>
  {:else}
    <!-- Show filings list -->
    <div class="filings-container">
      <!-- Selected filing is always visible -->
      {#if selectedFiling}
        <div class="filing-item selected-item" tabindex="0" role="option" aria-selected={true}>
          <h3>
            {selectedFiling.filing_type}
            {#if selectedFiling.filing_url}
              <a
                href={selectedFiling.filing_url}
                target="_blank"
                rel="noopener noreferrer"
                class="source-link">view source</a
              >
            {/if}
          </h3>
          {#if selectedFiling.period_of_report}
            <p>
              Fiscal Year Ending: <strong
                >{new Date(selectedFiling.period_of_report).toLocaleDateString()}</strong
              >
            </p>
          {/if}
        </div>
      {/if}

      <!-- Other filings (collapsible) -->
      <div
        class="filings-list scrollable collapsible-content"
        class:is-collapsed={isListCollapsed}
        role="listbox"
        aria-label="Filings list"
      >
        {#each filings as filing}
          <!-- Skip selected filing since it's already shown above -->
          {#if filing.id !== selectedFiling?.id}
            <div
              class="filing-item"
              onclick={() => selectFiling(filing)}
              onkeydown={(e) => handleKeyDown(e, filing)}
              tabindex="0"
              role="option"
              aria-selected={false}
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
                <p class="meta">
                  Fiscal Year Ending: <strong
                    >{new Date(filing.period_of_report).toLocaleDateString()}</strong
                  >
                </p>
              {/if}
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .filings-selector {
    /* Remove redundant styles that are now in utility classes */
    position: relative;
    min-height: 50px;
  }

  .placeholder {
    color: var(--color-text-light);
    font-style: italic;
  }

  /* New container to organize the layout */
  .filings-container {
    display: flex;
    flex-direction: column;
  }

  .filings-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    margin-top: var(--space-md);
    /* Max-height is already in collapsible-content class */
  }

  /* When collapsed, reduce height and fade out - handled by utility class now */
  .filings-list.is-collapsed {
    margin-top: 0;
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
    /* Transform and box-shadow now handled by hover-lift */
  }

  /* Remove border properties from this rule as they'll be handled by the selected-item class */
  .filing-item.selected-item {
    cursor: default;
    margin-bottom: var(--space-sm);
    padding: var(--space-md); /* Ensure consistent padding */
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

  /* Add margin for the button */
  .filing-item.selected-item p {
    margin-bottom: 0;
  }

  .source-link {
    font-size: 0.7rem;
    color: var(--color-primary);
    text-decoration: none;
  }

  .source-link:hover {
    text-decoration: underline;
  }

  /* Headings are now managed by utility classes */
</style>
