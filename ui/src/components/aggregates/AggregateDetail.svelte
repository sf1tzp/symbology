<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import { config } from '$utils/config';
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
  import { Button } from 'kampsy-ui';

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
      logger.info('completions_fetch_start', { aggregateId: aggregate.id });

      const completions = await fetchApi<CompletionResponse[]>(
        `${config.api.baseUrl}/aggregates/${aggregate.id}/completions`
      );
      sourceCompletions = completions;
      logger.info('completions_fetch_success', { count: completions.length });

      // Fetch document names for all source documents
      await fetchDocumentNames(completions);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('completions_fetch_failed', {
        error: errorMessage,
        aggregateId: aggregate.id,
      });
      error = errorMessage;
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
      logger.info('document_names_fetch_start', { documentCount: allDocumentIds.size });

      // Convert UUIDs to array for the POST endpoint
      const documentIds = Array.from(allDocumentIds);

      const documents = await fetchApi<Array<{ id: string; document_name: string }>>(
        `${config.api.baseUrl}/documents/by-ids`,
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

      logger.info('document_names_fetch_success', { count: documents.length });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('document_names_fetch_failed', { error: errorMessage });
      // Don't throw here - we can still show IDs as fallback
    }
  }

  function handleCompletionClick(completion: CompletionResponse) {
    logger.info('completion_selected', { completionId: completion.id });
    dispatch('completionSelected', completion);
  }

  function getDocumentName(docId: string): string {
    return documentNamesCache.get(docId) || `Document ID: ${docId}`;
  }
</script>

<div class="card content-container">
  <header class="aggregate-header">
    <div class="header-top">
      <BackButton on:back={actions.navigateBack} />
      <h1>
        {formatTitleCase(company.display_name)}
        '{formatTitleCase(formatDocumentType(aggregate.document_type))}'
      </h1>
    </div>
  </header>

  <section class="section-container">
    <div
      class="section-header"
      role="button"
      tabindex="0"
      onclick={() => (showDetails = !showDetails)}
      onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (showDetails = !showDetails)}
      aria-label={showDetails ? 'Hide details' : 'Show details'}
    >
      <h2 class="section-title">This summary was automatically generated. Click for details...</h2>
      <span class="icon" class:icon-collapsed={!showDetails}>▼</span>
    </div>

    <div class:collapsed={!showDetails}>
      <div class="details-content">
        <span class="meta-item">Generated on {formatDate(aggregate.created_at)}</span>
        <ModelConfig item={aggregate} showSystemPrompt={true} />

        <section class="section-container">
          <h3 class="section-title-small">Included Context:</h3>

          {#if loading}
            <LoadingState message="Loading source completions..." />
          {:else if error}
            <ErrorState
              message="Error loading source completions: {error}"
              onRetry={fetchSourceCompletions}
            />
          {:else if sourceCompletions.length > 0}
            <div class="list-container">
              {#each sourceCompletions as completion (completion.id)}
                <Button
                  variant="secondary"
                  size="medium"
                  onclick={() => handleCompletionClick(completion)}
                  onkeydown={(e) => e.key === 'Enter' && handleCompletionClick(completion)}
                  class="w-full text-left"
                >
                  {#if completion.source_documents?.length}
                    <ul>
                      {#each completion.source_documents as docId (docId)}
                        <li>Summary of {getDocumentName(docId)}</li>
                      {/each}
                    </ul>
                  {/if}
                </Button>
              {/each}
            </div>
          {:else}
            <div class="no-content">
              <p>No source completions found for this aggregate.</p>
            </div>
          {/if}
        </section>
      </div>
    </div>
  </section>

  <section class="section-container">
    {#if cleanContent(aggregate.content)}
      <div class="content-box">
        <MarkdownContent content={cleanContent(aggregate.content) || ''} />
      </div>
    {:else}
      <div class="no-content">
        <p>No content available for this aggregate.</p>
      </div>
    {/if}
  </section>
</div>

<style>
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
</style>
