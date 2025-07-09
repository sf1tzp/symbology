<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { AggregateResponse, CompanyResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

  const dispatch = createEventDispatcher<{
    aggregateSelected: AggregateResponse;
  }>();
  const logger = getLogger('AggregateSelector');

  // Props
  const { company } = $props<{ company: CompanyResponse | undefined }>();

  // Using Svelte 5 runes
  let aggregates = $state<AggregateResponse[]>([]);
  let selectedAggregate = $state<AggregateResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // New state variable for collapsible behavior
  let isListCollapsed = $state(false);
  let hoverTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on destroy
  onDestroy(() => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
  });

  // Watch for changes in company and fetch aggregates
  $effect(() => {
    logger.debug('[AggregateSelector] Effect watching company triggered', { company });
    if (company?.tickers?.[0]) {
      fetchAggregates();
    } else {
      logger.debug(
        '[AggregateSelector] Clearing aggregates and selectedAggregate because company is undefined'
      );
      aggregates = [];
      selectedAggregate = null;
      isListCollapsed = false; // Reset collapsed state when company changes
    }
  });

  async function fetchAggregates() {
    if (!company?.tickers?.[0]) {
      error = 'No company selected';
      return;
    }

    try {
      loading = true;
      error = null;
      const ticker = company.tickers[0];
      aggregates = await fetchApi<AggregateResponse[]>(
        `${config.api.baseUrl}/aggregates/by-ticker/${ticker}`
      );
      selectedAggregate = null;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching aggregates:', err);
      aggregates = [];
    } finally {
      loading = false;
    }
  }

  function selectAggregate(aggregate: AggregateResponse) {
    selectedAggregate = aggregate;
    dispatch('aggregateSelected', aggregate);

    // Collapse the aggregates list when an aggregate is selected
    if (aggregate) {
      isListCollapsed = true;
    }
  }

  // Functions to handle mouse events for expanding the list
  function handleMouseEnter() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (isListCollapsed && selectedAggregate) {
      isListCollapsed = false;
    }
  }

  function handleMouseLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (selectedAggregate && !loading) {
      // Add a small delay before collapsing to prevent jumpy UI
      hoverTimeout = setTimeout(() => {
        isListCollapsed = true;
      }, 300);
    }
  }

  // Function to handle focus events for accessibility
  function handleFocus() {
    if (isListCollapsed && selectedAggregate) {
      isListCollapsed = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent, aggregate: AggregateResponse) {
    // Select the aggregate when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectAggregate(aggregate);
    }
  }

  // Helper function to format document type for display
  function formatDocumentType(type: string): string {
    switch (type) {
      case 'MDA':
        return 'Management Discussion & Analysis';
      case 'RISK_FACTORS':
        return 'Risk Factors';
      case 'DESCRIPTION':
        return 'Business Description';
      default:
        return type;
    }
  }

  // Helper function to format model name for display
  function formatModelName(model: string): string {
    return model.replace('_', ' ').toUpperCase();
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="card section-container"
  class:has-selected={selectedAggregate !== null}
  class:is-collapsed={isListCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="section-title-small" class:is-collapsed={isListCollapsed}>Aggregates</h2>

  {#if !company}
    <p class="no-content">Please select a company to view its aggregates</p>
  {:else if loading}
    <div class="loading-container">
      <div class="loading-spinner normal"></div>
      <p class="loading-message">Loading aggregates...</p>
    </div>
  {:else if error}
    <p class="error-message">Error: {error}</p>
  {:else if aggregates.length === 0}
    <p class="no-content">No aggregates found for this company</p>
  {:else}
    <!-- Show aggregates list -->
    <div class="list-container">
      <!-- Selected aggregate is always visible -->
      {#if selectedAggregate}
        <div class="aggregate-item selected" tabindex="0" role="option" aria-selected={true}>
          <h3 class="section-title-small">{formatDocumentType(selectedAggregate.document_type)}</h3>
          <div class="meta-container">
            <div class="meta-item">
              Model: <strong>{formatModelName(selectedAggregate.model)}</strong>
            </div>
            {#if selectedAggregate.temperature}
              <div class="meta-item">Temperature: {selectedAggregate.temperature}</div>
            {/if}
            {#if selectedAggregate.total_duration}
              <div class="meta-item">
                Duration: {Math.round(selectedAggregate.total_duration)}s
              </div>
            {/if}
            <div class="meta-item">
              Created: {new Date(selectedAggregate.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      {/if}

      <!-- Other aggregates (collapsible) -->
      <div
        class="scrollable"
        class:collapsed={isListCollapsed}
        role="listbox"
        aria-label="Aggregates list"
      >
        <div class="list-container">
          {#each aggregates as aggregate (aggregate.id)}
            <!-- Skip selected aggregate since it's already shown above -->
            {#if aggregate.id !== selectedAggregate?.id}
              <button
                class="btn-item"
                onclick={() => selectAggregate(aggregate)}
                onkeydown={(e) => handleKeyDown(e, aggregate)}
                role="option"
                aria-selected={false}
              >
                <div>
                  <h3 class="aggregate-title">{formatDocumentType(aggregate.document_type)}</h3>
                  <div class="aggregate-meta-container">
                    <div class="meta-item">
                      Model: <strong>{formatModelName(aggregate.model)}</strong>
                    </div>
                    {#if aggregate.temperature}
                      <div class="meta-item">Temperature: {aggregate.temperature}</div>
                    {/if}
                    {#if aggregate.total_duration}
                      <div class="meta-item">Duration: {Math.round(aggregate.total_duration)}s</div>
                    {/if}
                    <div class="meta-item">
                      Created: {new Date(aggregate.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </button>
            {/if}
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  /* Custom styles for aggregate-specific elements */
  .aggregate-item {
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-sm);
  }

  .aggregate-title {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
    font-size: 1rem;
    font-weight: var(--font-weight-medium);
  }

  .aggregate-meta-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  /* Visual state indicators for component */
  .has-selected {
    border-color: var(--color-primary);
  }

  .is-collapsed {
    opacity: 0.8;
  }
</style>
