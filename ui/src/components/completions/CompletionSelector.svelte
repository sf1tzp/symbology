<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompletionResponse, AggregateResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

  const dispatch = createEventDispatcher<{
    completionSelected: CompletionResponse;
  }>();
  const logger = getLogger('CompletionSelector');

  // Props
  const { aggregate } = $props<{ aggregate: AggregateResponse | undefined }>();

  // Using Svelte 5 runes
  let completions = $state<CompletionResponse[]>([]);
  let selectedCompletion = $state<CompletionResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // New state variable for collapsible behavior
  let isListCollapsed = $state(false);
  let hoverTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on destroy
  onDestroy(() => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
  });

  // Watch for changes in aggregate and fetch completions
  $effect(() => {
    logger.debug('[CompletionSelector] Effect watching aggregate triggered', { aggregate });
    if (aggregate?.id) {
      fetchCompletions();
    } else {
      logger.debug(
        '[CompletionSelector] Clearing completions and selectedCompletion because aggregate is undefined'
      );
      completions = [];
      selectedCompletion = null;
      isListCollapsed = false; // Reset collapsed state when aggregate changes
    }
  });

  async function fetchCompletions() {
    if (!aggregate?.id) {
      error = 'No aggregate selected';
      return;
    }

    try {
      loading = true;
      error = null;
      completions = await fetchApi<CompletionResponse[]>(
        `${config.api.baseUrl}/aggregates/${aggregate.id}/completions`
      );
      selectedCompletion = null;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching completions:', err);
      completions = [];
    } finally {
      loading = false;
    }
  }

  function selectCompletion(completion: CompletionResponse) {
    selectedCompletion = completion;
    dispatch('completionSelected', completion);

    // Collapse the completions list when a completion is selected
    if (completion) {
      isListCollapsed = true;
    }
  }

  // Functions to handle mouse events for expanding the list
  function handleMouseEnter() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (isListCollapsed && selectedCompletion) {
      isListCollapsed = false;
    }
  }

  function handleMouseLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (selectedCompletion && !loading) {
      // Add a small delay before collapsing to prevent jumpy UI
      hoverTimeout = setTimeout(() => {
        isListCollapsed = true;
      }, 300);
    }
  }

  // Function to handle focus events for accessibility
  function handleFocus() {
    if (isListCollapsed && selectedCompletion) {
      isListCollapsed = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent, completion: CompletionResponse) {
    // Select the completion when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectCompletion(completion);
    }
  }

  // Helper function to format model name for display
  function formatModelName(model: string): string {
    return model.replace('_', ' ').toUpperCase();
  }

  // Helper function to format completion ID for display
  function formatCompletionId(id: string): string {
    return id.substring(0, 8) + '...';
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="completions-selector card collapsible-component"
  class:has-selected={selectedCompletion !== null}
  class:is-collapsed={isListCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="collapsible-heading" class:is-collapsed={isListCollapsed}>Completions</h2>

  {#if !aggregate}
    <p class="placeholder">Please select an aggregate to view its completions</p>
  {:else if loading}
    <p>Loading completions...</p>
  {:else if error}
    <p class="error-message">Error: {error}</p>
  {:else if completions.length === 0}
    <p>No completions found for this aggregate</p>
  {:else}
    <!-- Show completions list -->
    <div class="completions-container">
      <!-- Selected completion is always visible -->
      {#if selectedCompletion}
        <div class="completion-item selected-item" tabindex="0" role="option" aria-selected={true}>
          <h3>Completion {formatCompletionId(selectedCompletion.id)}</h3>
          <div class="completion-meta">
            <p class="model-info">
              Model: <strong>{formatModelName(selectedCompletion.model)}</strong>
            </p>
            {#if selectedCompletion.temperature}
              <p class="config-detail">Temperature: {selectedCompletion.temperature}</p>
            {/if}
            {#if selectedCompletion.top_p}
              <p class="config-detail">Top-p: {selectedCompletion.top_p}</p>
            {/if}
            {#if selectedCompletion.num_ctx}
              <p class="config-detail">Context: {selectedCompletion.num_ctx}</p>
            {/if}
            {#if selectedCompletion.total_duration}
              <p class="config-detail">
                Duration: {Math.round(selectedCompletion.total_duration)}s
              </p>
            {/if}
            {#if selectedCompletion.source_documents?.length}
              <p class="source-count">
                Sources: {selectedCompletion.source_documents.length} documents
              </p>
            {/if}
            <p class="timestamp">
              Created: {new Date(selectedCompletion.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      {/if}

      <!-- Other completions (collapsible) -->
      <div
        class="completions-list scrollable collapsible-content"
        class:is-collapsed={isListCollapsed}
        role="listbox"
        aria-label="Completions list"
      >
        {#each completions as completion (completion.id)}
          <!-- Skip selected completion since it's already shown above -->
          {#if completion.id !== selectedCompletion?.id}
            <div
              class="completion-item"
              onclick={() => selectCompletion(completion)}
              onkeydown={(e) => handleKeyDown(e, completion)}
              tabindex="0"
              role="option"
              aria-selected={false}
            >
              <h3>Completion {formatCompletionId(completion.id)}</h3>
              <div class="completion-meta">
                <p class="model-info">
                  Model: <strong>{formatModelName(completion.model)}</strong>
                </p>
                {#if completion.temperature}
                  <p class="config-detail">Temperature: {completion.temperature}</p>
                {/if}
                {#if completion.top_p}
                  <p class="config-detail">Top-p: {completion.top_p}</p>
                {/if}
                {#if completion.num_ctx}
                  <p class="config-detail">Context: {completion.num_ctx}</p>
                {/if}
                {#if completion.total_duration}
                  <p class="config-detail">Duration: {Math.round(completion.total_duration)}s</p>
                {/if}
                {#if completion.source_documents?.length}
                  <p class="source-count">
                    Sources: {completion.source_documents.length} documents
                  </p>
                {/if}
                <p class="timestamp">
                  Created: {new Date(completion.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .completions-selector {
    position: relative;
    min-height: 50px;
  }

  .placeholder {
    color: var(--color-text-light);
    font-style: italic;
  }

  .completions-container {
    display: flex;
    flex-direction: column;
  }

  .completions-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    margin-top: var(--space-md);
  }

  .completions-list.is-collapsed {
    margin-top: 0;
  }

  .completion-item {
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid var(--color-border);
  }

  .completion-item:hover {
    border-color: var(--color-primary);
  }

  .completion-item.selected-item {
    cursor: default;
    margin-bottom: var(--space-sm);
    padding: var(--space-md);
  }

  .completion-item h3 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
    font-size: 1.1rem;
    font-family: monospace;
  }

  .completion-meta {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  .completion-meta p {
    margin: 0;
    font-size: 0.9rem;
  }

  .model-info {
    color: var(--color-primary);
    font-weight: 500;
  }

  .config-detail {
    color: var(--color-text-light);
    font-family: monospace;
    font-size: 0.8rem;
  }

  .source-count {
    color: var(--color-text);
    font-weight: 500;
    font-size: 0.85rem;
  }

  .timestamp {
    color: var(--color-text-light);
    font-size: 0.8rem;
  }
</style>
