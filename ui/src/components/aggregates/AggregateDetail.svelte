<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type {
    AggregateResponse,
    CompanyResponse,
    CompletionResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { formatDate, cleanContent, formatDocumentType, formatTitleCase } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import ModelConfig from '$components/ui/ModelConfig.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import BackButton from '$components/ui/BackButton.svelte';
  import { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('AggregateDetail');
  const dispatch = createEventDispatcher<{
    completionSelected: CompletionResponse;
  }>();

  const { aggregate, company } = $props<{
    aggregate: AggregateResponse;
    company?: CompanyResponse;
  }>();

  let sourceCompletions = $state<CompletionResponse[]>([]);
  let documentNamesCache = $state<Map<string, string>>(new Map());
  let loading = $state(false);
  let error = $state<string | null>(null);
  let showDetails = $state(false);

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

      // Fetch document names for all source documents
      await fetchDocumentNames(completions);
    } catch (err) {
      logger.error('[AggregateDetail] Failed to fetch source completions', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load source completions';
      sourceCompletions = [];
    } finally {
      loading = false;
    }
  }

  async function fetchDocumentNames(completions: CompletionResponse[]) {
    // Collect all unique document IDs
    const allDocumentIds = new Set<string>();
    for (const completion of completions) {
      if (completion.source_documents) {
        for (const docId of completion.source_documents) {
          allDocumentIds.add(docId);
        }
      }
    }

    if (allDocumentIds.size === 0) return;

    try {
      logger.debug('[AggregateDetail] Fetching document names', {
        documentCount: allDocumentIds.size,
      });

      // Convert UUIDs to array for the POST endpoint
      const documentIds = Array.from(allDocumentIds);

      const documents = await fetchApi<Array<{ id: string; document_name: string }>>(
        `/api/documents/by-ids`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(documentIds),
        }
      );

      // Update the cache with document names
      for (const doc of documents) {
        documentNamesCache.set(doc.id, doc.document_name);
      }

      logger.debug('[AggregateDetail] Fetched document names', { count: documents.length });
    } catch (err) {
      logger.error('[AggregateDetail] Failed to fetch document names', { error: err });
      // Don't throw here - we can still show IDs as fallback
    }
  }

  function handleCompletionClick(completion: CompletionResponse) {
    logger.debug('[AggregateDetail] Completion selected', { completionId: completion.id });
    dispatch('completionSelected', completion);
  }

  function getDocumentName(docId: string): string {
    return documentNamesCache.get(docId) || `Document ID: ${docId}`;
  }
</script>

<div class="aggregate-detail card">
  <header class="aggregate-header">
    <div class="header-top">
      <BackButton on:back={actions.navigateBack} />
      <h1>
        Analysis of
        {formatTitleCase(company.display_name)}
        '{formatTitleCase(formatDocumentType(aggregate.document_type))}' over time
      </h1>
    </div>
    <div class="aggregate-meta"></div>
  </header>

  <section class="summary-section">
    <div
      class="section-header"
      role="button"
      tabindex="0"
      onclick={() => (showDetails = !showDetails)}
      onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (showDetails = !showDetails)}
      aria-label={showDetails ? 'Hide details' : 'Show details'}
    >
      <h2>This summary was automatically generated. Click for details...</h2>
      <span class="toggle-icon" class:collapsed={!showDetails}>▼</span>
    </div>

    {#if showDetails}
      <div class="details-content">
        <span class="created-date">Generated on {formatDate(aggregate.created_at)}</span>
        <ModelConfig item={aggregate} showSystemPrompt={true} />

        <section class="source-completions-section">
          <h3>Included Context:</h3>

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
                  {#if completion.source_documents?.length}
                    <ul>
                      {#each completion.source_documents as docId (docId)}
                        <li>Summary of {getDocumentName(docId)}</li>
                      {/each}
                    </ul>
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
      </div>
    {/if}
  </section>

  <section class="content-section">
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

  <!-- <section class="ratings-section">
    <h2>Ratings</h2>
    <div class="unimplemented">
      <p>Rating system is not yet implemented</p>
    </div>
  </section> -->
</div>

<style>
  .aggregate-detail {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  .header-top {
    display: flex;
    align-items: flex-start;
    gap: var(--space-md);
    margin-bottom: var(--space-sm);
  }

  .aggregate-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
    flex: 1;
  }

  .aggregate-meta {
    display: flex;
    gap: var(--space-md);
    align-items: center;
    margin-top: var(--space-sm);
  }

  .created-date {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-md);
    cursor: pointer;
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    transition: background-color 0.2s ease;
  }

  /* .section-header:hover {
    background-color: var(--color-background);
  } */

  /* .section-header:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  } */

  .section-header h2 {
    margin: 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
    flex: 1;
  }

  .toggle-icon {
    display: inline-block;
    font-size: 0.8rem;
    color: var(--color-text-light);
    transition: transform 0.2s ease;
  }

  .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

  .details-content {
    animation: slideDown 0.3s ease-out;
    overflow: hidden;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      max-height: 0;
    }
    to {
      opacity: 1;
      max-height: 1000px;
    }
  }

  .summary-section {
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
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
  }

  .completion-item {
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .completion-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
    border-color: var(--color-primary);
  }

  @media (max-width: 768px) {
    .aggregate-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
