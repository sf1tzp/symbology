<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompletionResponse, AggregateResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';
  import { Spinner } from 'kampsy-ui';

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
  class="card section-container"
  class:has-selected={selectedCompletion !== null}
  class:is-collapsed={isListCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="section-title-small" class:is-collapsed={isListCollapsed}>Completions</h2>

  {#if !aggregate}
    <p class="no-content">Please select an aggregate to view its completions</p>
  {:else if loading}
    <div class="flex flex-col items-center p-8 gap-4">
      <Spinner size="medium" />
      <p class="text-[var(--color-text)] opacity-80 text-sm">Loading completions...</p>
    </div>
  {:else if error}
    <p class="error-message">Error: {error}</p>
  {:else if completions.length === 0}
    <p class="no-content">No completions found for this aggregate</p>
  {:else}
    <!-- Show completions list -->
    <div class="list-container">
      <!-- Selected completion is always visible -->
      {#if selectedCompletion}
        <div class="completion-item selected" tabindex="0" role="option" aria-selected={true}>
          <h3 class="completion-title">Completion {formatCompletionId(selectedCompletion.id)}</h3>
          <div class="meta-container">
            <div class="meta-item">
              Model: <strong>{formatModelName(selectedCompletion.model)}</strong>
            </div>
            {#if selectedCompletion.temperature}
              <div class="meta-item">Temperature: {selectedCompletion.temperature}</div>
            {/if}
            {#if selectedCompletion.top_p}
              <div class="meta-item">Top-p: {selectedCompletion.top_p}</div>
            {/if}
            {#if selectedCompletion.num_ctx}
              <div class="meta-item">Context: {selectedCompletion.num_ctx}</div>
            {/if}
            {#if selectedCompletion.total_duration}
              <div class="meta-item">
                Duration: {Math.round(selectedCompletion.total_duration)}s
              </div>
            {/if}
            {#if selectedCompletion.source_documents?.length}
              <div class="meta-item">
                Sources: {selectedCompletion.source_documents.length} documents
              </div>
            {/if}
            <div class="meta-item">
              Created: {new Date(selectedCompletion.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      {/if}

      <!-- Other completions (collapsible) -->
      <div
        class="scrollable"
        class:collapsed={isListCollapsed}
        role="listbox"
        aria-label="Completions list"
      >
        <div class="list-container">
          {#each completions as completion (completion.id)}
            <!-- Skip selected completion since it's already shown above -->
            {#if completion.id !== selectedCompletion?.id}
              <button
                class="btn-item"
                onclick={() => selectCompletion(completion)}
                onkeydown={(e) => handleKeyDown(e, completion)}
                role="option"
                aria-selected={false}
              >
                <div>
                  <h3 class="completion-title">Completion {formatCompletionId(completion.id)}</h3>
                  <div class="completion-meta-container">
                    <div class="meta-item">
                      Model: <strong>{formatModelName(completion.model)}</strong>
                    </div>
                    {#if completion.temperature}
                      <div class="meta-item">Temperature: {completion.temperature}</div>
                    {/if}
                    {#if completion.top_p}
                      <div class="meta-item">Top-p: {completion.top_p}</div>
                    {/if}
                    {#if completion.num_ctx}
                      <div class="meta-item">Context: {completion.num_ctx}</div>
                    {/if}
                    {#if completion.total_duration}
                      <div class="meta-item">
                        Duration: {Math.round(completion.total_duration)}s
                      </div>
                    {/if}
                    {#if completion.source_documents?.length}
                      <div class="meta-item">
                        Sources: {completion.source_documents.length} documents
                      </div>
                    {/if}
                    <div class="meta-item">
                      Created: {new Date(completion.created_at).toLocaleDateString()}
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
  /* Custom styles for completion-specific elements */
  .completion-item {
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-sm);
  }

  .completion-title {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
    font-size: 1rem;
    font-weight: var(--font-weight-medium);
    font-family: monospace;
  }

  .completion-meta-container {
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
