<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompletionResponse, DocumentResponse } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import {
    formatDate,
    formatModelName,
    cleanContent,
    getDocumentTypeName,
  } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import ModelConfig from '$components/ui/ModelConfig.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';

  const logger = getLogger('CompletionDetail');
  const dispatch = createEventDispatcher<{
    documentSelected: DocumentResponse;
  }>();

  const { completion } = $props<{
    completion: CompletionResponse;
  }>();

  let sourceDocuments = $state<DocumentResponse[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Fetch source documents when completion changes
  $effect(() => {
    if (completion && completion.source_documents?.length) {
      fetchSourceDocuments();
    } else {
      sourceDocuments = [];
    }
  });

  async function fetchSourceDocuments() {
    loading = true;
    error = null;
    try {
      logger.debug('[CompletionDetail] Fetching source documents for completion', {
        completionId: completion.id,
        documentIds: completion.source_documents,
      });

      // Fetch each document individually since we don't have a bulk endpoint
      const documentPromises = completion.source_documents!.map((docId: string) =>
        fetchApi<DocumentResponse>(`/api/documents/${docId}`)
      );

      const documents = await Promise.all(documentPromises);
      sourceDocuments = documents;
      logger.debug('[CompletionDetail] Fetched source documents', { count: documents.length });
    } catch (err) {
      logger.error('[CompletionDetail] Failed to fetch source documents', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load source documents';
      sourceDocuments = [];
    } finally {
      loading = false;
    }
  }

  function handleDocumentClick(document: DocumentResponse) {
    logger.debug('[CompletionDetail] Document selected', {
      documentId: document.id,
      documentName: document.document_name,
    });
    dispatch('documentSelected', document);
  }

  // Prepare document meta items for each source document
  function getDocumentMetaItems(document: DocumentResponse) {
    return [
      { label: 'Document Name', value: document.document_name },
      ...(document.filing_id
        ? [{ label: 'Filing ID', value: document.filing_id, mono: true }]
        : []),
    ];
  }
</script>

<div class="completion-detail card">
  <header class="completion-header">
    <h1>Completion Overview</h1>
    <div class="completion-meta">
      <span class="model-badge">{formatModelName(completion.model)}</span>
      <span class="created-date">{formatDate(completion.created_at)}</span>
    </div>
  </header>

  <section class="summary-section">
    <h2>Summary</h2>
    <ModelConfig item={completion} showSystemPrompt={true} />
  </section>

  <section class="content-section">
    <h2>Content</h2>
    {#if cleanContent(completion.content)}
      <div class="content-display">
        <MarkdownContent content={cleanContent(completion.content) || ''} />
      </div>
    {:else}
      <div class="no-content">
        <p>No content available for this completion.</p>
      </div>
    {/if}
  </section>

  <section class="sources-section">
    <h2>Sources</h2>

    {#if loading}
      <LoadingState message="Loading source documents..." />
    {:else if error}
      <ErrorState
        message="Error loading source documents: {error}"
        onRetry={fetchSourceDocuments}
      />
    {:else if sourceDocuments.length > 0}
      <div class="sources-list">
        {#each sourceDocuments as document (document.id)}
          <div
            class="source-item"
            role="button"
            tabindex="0"
            onclick={() => handleDocumentClick(document)}
            onkeydown={(e) => e.key === 'Enter' && handleDocumentClick(document)}
          >
            <div class="source-header">
              <h3>{getDocumentTypeName(document.document_name)}</h3>
              <span class="source-type">Document</span>
            </div>

            <MetaItems items={getDocumentMetaItems(document)} variant="surface" />

            <div class="source-preview">
              <p>Click to view raw source material from SEC filing</p>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="no-sources">
        <p>No source documents found for this completion.</p>
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
  .completion-detail {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  .completion-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
  }

  .completion-meta {
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
  .sources-section h2,
  .ratings-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .no-content,
  .no-sources {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }

  .sources-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .source-item {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .source-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
    border-color: var(--color-primary);
  }

  .source-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-sm);
  }

  .source-header h3 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1rem;
    font-weight: var(--font-weight-bold);
  }

  .source-type {
    background-color: var(--color-secondary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.8rem;
  }

  .source-preview {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px dashed var(--color-border);
    margin-top: var(--space-sm);
  }

  .source-preview p {
    margin: 0;
    font-size: 0.9rem;
  }

  .unimplemented {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }

  @media (max-width: 768px) {
    .completion-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
