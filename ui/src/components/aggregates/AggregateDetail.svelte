<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { AggregateResponse, CompletionResponse } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { formatDate, formatModelName, cleanContent, formatDocumentType } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import ModelConfig from '$components/ui/ModelConfig.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';

  const logger = getLogger('AggregateDetail');
  const dispatch = createEventDispatcher<{
    completionSelected: CompletionResponse;
  }>();

  const { aggregate } = $props<{
    aggregate: AggregateResponse;
  }>();

  let sourceCompletions = $state<CompletionResponse[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Fetch source completions when aggregate changes
  $effect(() => {
    if (aggregate) {
      fetchSourceCompletions();
    }
  });

  async function fetchSourceCompletions() {
    loading = true;
    error = null;
    try {
      logger.debug('[AggregateDetail] Fetching source completions for aggregate', {
        aggregateId: aggregate.id,
      });

      const completions = await fetchApi<CompletionResponse[]>(
        `/api/aggregates/${aggregate.id}/completions`
      );
      sourceCompletions = completions;
      logger.debug('[AggregateDetail] Fetched source completions', { count: completions.length });
    } catch (err) {
      logger.error('[AggregateDetail] Failed to fetch source completions', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load source completions';
      sourceCompletions = [];
    } finally {
      loading = false;
    }
  }

  function handleCompletionClick(completion: CompletionResponse) {
    logger.debug('[AggregateDetail] Completion selected', { completionId: completion.id });
    dispatch('completionSelected', completion);
  }

  // Prepare completion meta items for each source completion
  function getCompletionMetaItems(completion: CompletionResponse) {
    return [
      { label: 'Model', value: formatModelName(completion.model) },
      ...(completion.temperature ? [{ label: 'Temperature', value: completion.temperature }] : []),
      { label: 'Created', value: formatDate(completion.created_at) },
      ...(completion.source_documents?.length
        ? [
            {
              label: 'Documents',
              value: `${completion.source_documents.length} source${completion.source_documents.length === 1 ? '' : 's'}`,
            },
          ]
        : []),
    ];
  }
</script>

<div class="aggregate-detail card">
  <header class="aggregate-header">
    <h1>{formatDocumentType(aggregate.document_type)}</h1>
    <div class="aggregate-meta">
      <span class="model-badge">{formatModelName(aggregate.model)}</span>
      <span class="created-date">{formatDate(aggregate.created_at)}</span>
    </div>
  </header>

  <section class="summary-section">
    <h2>Summary</h2>

    {#if cleanContent(aggregate.summary)}
      <div class="summary-text">
        <MarkdownContent content={cleanContent(aggregate.summary) || ''} />
      </div>
    {/if}

    <ModelConfig item={aggregate} showSystemPrompt={true} />
  </section>

  <section class="content-section">
    <h2>Content</h2>
    {#if cleanContent(aggregate.content)}
      <div class="content-display">
        <MarkdownContent content={cleanContent(aggregate.content) || ''} />
      </div>
    {:else}
      <div class="no-content">
        <p>No content available for this aggregate.</p>
      </div>
    {/if}
  </section>

  <section class="source-completions-section">
    <h2>Links to Source Completions</h2>

    {#if loading}
      <LoadingState message="Loading source completions..." />
    {:else if error}
      <ErrorState
        message="Error loading source completions: {error}"
        onRetry={fetchSourceCompletions}
      />
    {:else if sourceCompletions.length > 0}
      <div class="completions-list">
        {#each sourceCompletions as completion (completion.id)}
          <div
            class="completion-item"
            role="button"
            tabindex="0"
            onclick={() => handleCompletionClick(completion)}
            onkeydown={(e) => e.key === 'Enter' && handleCompletionClick(completion)}
          >
            <div class="completion-header">
              <h3>Completion #{completion.id}</h3>
              <span class="completion-model">{formatModelName(completion.model)}</span>
            </div>

            <MetaItems items={getCompletionMetaItems(completion)} variant="surface" />

            {#if completion.source_documents?.length}
              <div class="document-list">
                <h4>Source Documents ({completion.source_documents.length})</h4>
                <ul>
                  {#each completion.source_documents as docId (docId)}
                    <li>Document ID: {docId}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="no-completions">
        <p>No source completions found for this aggregate.</p>
      </div>
    {/if}
  </section>

  <section class="ratings-section">
    <h2>Ratings</h2>
    <div class="unimplemented">
      <p>Rating system is not yet implemented</p>
    </div>
  </section>
</div>

<style>
  .aggregate-detail {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  .aggregate-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
  }

  .aggregate-meta {
    display: flex;
    gap: var(--space-md);
    align-items: center;
    margin-top: var(--space-sm);
  }

  .model-badge {
    background-color: var(--color-primary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.9rem;
  }

  .created-date {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .summary-section h2,
  .content-section h2,
  .source-completions-section h2,
  .ratings-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .summary-text {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
  }

  .content-display {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .no-content,
  .no-completions {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }

  .completions-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .completion-item {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .completion-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
    border-color: var(--color-primary);
  }

  .completion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-sm);
  }

  .completion-header h3 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1rem;
    font-weight: var(--font-weight-bold);
  }

  .completion-model {
    background-color: var(--color-secondary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.8rem;
  }

  .document-list {
    margin-top: var(--space-sm);
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .document-list h4 {
    margin: 0 0 var(--space-xs) 0;
    color: var(--color-text);
    font-size: 0.9rem;
  }

  .document-list ul {
    list-style-type: disc;
    padding-left: 1.5rem;
    margin: 0;
  }

  .document-list li {
    color: var(--color-text-light);
    font-size: 0.8rem;
    margin-bottom: var(--space-xs);
  }

  .unimplemented {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }

  @media (max-width: 768px) {
    .aggregate-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
