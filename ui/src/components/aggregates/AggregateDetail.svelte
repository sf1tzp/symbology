<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type {
    AggregateResponse,
    CompletionResponse,
    DocumentResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { marked } from 'marked';

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

  // Store document details for each completion
  let documentsByCompletion = $state<Map<string, DocumentResponse[]>>(new Map());
  let loadingDocuments = $state<Set<string>>(new Set());

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

      // Fetch document details for each completion
      await fetchDocumentsForCompletions(completions);
    } catch (err) {
      logger.error('[AggregateDetail] Failed to fetch source completions', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load source completions';
      sourceCompletions = [];
    } finally {
      loading = false;
    }
  }

  async function fetchDocumentsForCompletions(completions: CompletionResponse[]) {
    const newDocumentsByCompletion = new Map<string, DocumentResponse[]>();
    const newLoadingDocuments = new Set<string>();

    for (const completion of completions) {
      if (completion.source_documents?.length) {
        newLoadingDocuments.add(completion.id);
        try {
          const documents = await Promise.all(
            completion.source_documents.map(async (docId) => {
              const doc = await fetchApi<DocumentResponse>(`/api/documents/${docId}`);
              return doc;
            })
          );
          newDocumentsByCompletion.set(completion.id, documents);
        } catch (err) {
          logger.error('[AggregateDetail] Failed to fetch documents for completion', {
            completionId: completion.id,
            error: err,
          });
          newDocumentsByCompletion.set(completion.id, []);
        } finally {
          newLoadingDocuments.delete(completion.id);
        }
      } else {
        newDocumentsByCompletion.set(completion.id, []);
      }
    }

    documentsByCompletion = newDocumentsByCompletion;
    loadingDocuments = newLoadingDocuments;
  }

  function handleCompletionClick(completion: CompletionResponse) {
    logger.debug('[AggregateDetail] Completion selected', { completionId: completion.id });
    dispatch('completionSelected', completion);
  }

  function formatDate(dateString: string | undefined) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  }

  function getDocumentTypeName(docType: string | undefined) {
    switch (docType) {
      case 'MDA':
      case 'management_discussion':
        return 'Management Discussion & Analysis';
      case 'DESCRIPTION':
      case 'business_description':
        return 'Business Description';
      case 'RISK_FACTORS':
      case 'risk_factors':
        return 'Risk Factors';
      default:
        return docType || 'Unknown Analysis';
    }
  }

  function getCompletionDisplayName(completion: CompletionResponse): string {
    const documents = documentsByCompletion.get(completion.id) || [];

    if (documents.length === 0) {
      return 'Completion';
    } else if (documents.length === 1) {
      return documents[0].document_name;
    } else {
      // Multiple documents - show first document name with count
      return `${documents[0].document_name} (+${documents.length - 1} more)`;
    }
  }

  function cleanAggregateContent(content: string | undefined): string | undefined {
    if (!content) return undefined;

    // Remove <think>...</think> blocks and any content before them
    let cleaned = content.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

    // Also handle cases where there might be thinking content without tags
    cleaned = cleaned.replace(
      /^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
      ''
    );

    // Trim any remaining whitespace
    cleaned = cleaned.trim();

    return cleaned || undefined;
  }

  function renderMarkdown(text: string): string {
    const result = marked.parse(text, {
      breaks: true,
      gfm: true,
      async: false,
    });
    return typeof result === 'string' ? result : '';
  }
</script>

<div class="aggregate-detail card">
  <header class="aggregate-header">
    <h1>{getDocumentTypeName(aggregate.document_type)}</h1>
    <div class="aggregate-meta">
      <span class="model-badge">{aggregate.model.replace('_', ' ').toUpperCase()}</span>
      <span class="created-date">{formatDate(aggregate.created_at)}</span>
    </div>
  </header>

  <section class="summary-section">
    <h2>Summary</h2>

    {#if cleanAggregateContent(aggregate.summary)}
      <div class="summary-text">
        {@html renderMarkdown(cleanAggregateContent(aggregate.summary) || '')}
      </div>
    {/if}

    <div class="model-config">
      <h3>Model Configuration</h3>
      <div class="config-grid">
        <div class="config-item">
          <span class="label">Model:</span>
          <span>{aggregate.model.replace('_', ' ').toUpperCase()}</span>
        </div>
        {#if aggregate.temperature !== null && aggregate.temperature !== undefined}
          <div class="config-item">
            <span class="label">Temperature:</span>
            <span>{aggregate.temperature}</span>
          </div>
        {/if}
        {#if aggregate.top_p !== null && aggregate.top_p !== undefined}
          <div class="config-item">
            <span class="label">Top-p:</span>
            <span>{aggregate.top_p}</span>
          </div>
        {/if}
        {#if aggregate.num_ctx !== null && aggregate.num_ctx !== undefined}
          <div class="config-item">
            <span class="label">Context Window:</span>
            <span>{aggregate.num_ctx.toLocaleString()}</span>
          </div>
        {/if}
        {#if aggregate.total_duration !== null && aggregate.total_duration !== undefined}
          <div class="config-item">
            <span class="label">Duration:</span>
            <span>{aggregate.total_duration.toFixed(2)}s</span>
          </div>
        {/if}
      </div>
    </div>

    {#if aggregate.system_prompt_id}
      <div class="response-warnings">
        <h3>Response Information</h3>
        <div class="warning-item">
          <span class="label">System Prompt ID:</span>
          <span class="mono">{aggregate.system_prompt_id}</span>
        </div>
      </div>
    {/if}
  </section>

  <section class="content-section">
    <h2>Content</h2>
    {#if cleanAggregateContent(aggregate.content)}
      <div class="content-display">
        {@html renderMarkdown(cleanAggregateContent(aggregate.content) || '')}
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
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <p>Loading source completions...</p>
      </div>
    {:else if error}
      <div class="error-message">
        <p>Error loading source completions: {error}</p>
        <button onclick={fetchSourceCompletions} class="retry-button">Retry</button>
      </div>
    {:else if sourceCompletions.length > 0}
      <div class="completions-list">
        {#each sourceCompletions as completion}
          <div
            class="completion-item"
            role="button"
            tabindex="0"
            onclick={() => handleCompletionClick(completion)}
            onkeydown={(e) => e.key === 'Enter' && handleCompletionClick(completion)}
          >
            <div class="completion-header">
              <div class="completion-title">
                {#if loadingDocuments.has(completion.id)}
                  <div class="loading-title">
                    <div class="small-spinner"></div>
                    <span>Loading...</span>
                  </div>
                {:else}
                  <h3>{getCompletionDisplayName(completion)}</h3>
                {/if}
              </div>
              <span class="completion-model"
                >{completion.model.replace('_', ' ').toUpperCase()}</span
              >
            </div>

            <!-- Show document list if multiple documents -->
            {#if !loadingDocuments.has(completion.id)}
              {@const documents = documentsByCompletion.get(completion.id) || []}
              {#if documents.length > 1}
                <div class="document-list">
                  <h4>Source Documents:</h4>
                  <ul>
                    {#each documents as document}
                      <li>{document.document_name}</li>
                    {/each}
                  </ul>
                </div>
              {/if}
            {/if}

            <div class="completion-meta">
              <div class="meta-item">
                <span class="label">Created:</span>
                <span>{formatDate(completion.created_at)}</span>
              </div>
              {#if completion.temperature !== null && completion.temperature !== undefined}
                <div class="meta-item">
                  <span class="label">Temperature:</span>
                  <span>{completion.temperature}</span>
                </div>
              {/if}
              {#if completion.total_duration !== null && completion.total_duration !== undefined}
                <div class="meta-item">
                  <span class="label">Duration:</span>
                  <span>{completion.total_duration.toFixed(1)}s</span>
                </div>
              {/if}
              {#if completion.source_documents?.length}
                <div class="meta-item">
                  <span class="label">Source Docs:</span>
                  <span>{completion.source_documents.length}</span>
                </div>
              {/if}
            </div>
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

  .model-config h3,
  .response-warnings h3 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-size: 1rem;
  }

  .config-grid {
    display: grid;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  .config-item,
  .warning-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .config-item .label,
  .warning-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
  }

  .config-item span:not(.label),
  .warning-item span:not(.label) {
    color: var(--color-text-light);
  }

  .mono {
    font-family: monospace;
    font-size: 0.9rem;
  }

  .summary-text {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
  }

  .summary-text :global(p) {
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.6;
    color: var(--color-text);
  }

  .summary-text :global(p:last-child) {
    margin-bottom: 0;
  }

  .summary-text :global(h1),
  .summary-text :global(h2),
  .summary-text :global(h3),
  .summary-text :global(h4),
  .summary-text :global(h5),
  .summary-text :global(h6) {
    margin: var(--space-md) 0 var(--space-sm) 0;
    color: var(--color-primary);
  }

  .summary-text :global(h1:first-child),
  .summary-text :global(h2:first-child),
  .summary-text :global(h3:first-child),
  .summary-text :global(h4:first-child),
  .summary-text :global(h5:first-child),
  .summary-text :global(h6:first-child) {
    margin-top: 0;
  }

  .summary-text :global(ul),
  .summary-text :global(ol) {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .summary-text :global(li) {
    margin: var(--space-xs) 0;
    line-height: 1.5;
  }

  .summary-text :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .summary-text :global(em) {
    font-style: italic;
  }

  .summary-text :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.9em;
  }

  .summary-text :global(pre) {
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: var(--space-sm) 0;
  }

  .summary-text :global(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--space-md);
    margin: var(--space-sm) 0;
    font-style: italic;
    color: var(--color-text-light);
  }

  .content-display {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .content-display :global(p) {
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.6;
    color: var(--color-text);
    word-break: break-word;
  }

  .content-display :global(p:last-child) {
    margin-bottom: 0;
  }

  .content-display :global(h1),
  .content-display :global(h2),
  .content-display :global(h3),
  .content-display :global(h4),
  .content-display :global(h5),
  .content-display :global(h6) {
    margin: var(--space-md) 0 var(--space-sm) 0;
    color: var(--color-primary);
  }

  .content-display :global(h1:first-child),
  .content-display :global(h2:first-child),
  .content-display :global(h3:first-child),
  .content-display :global(h4:first-child),
  .content-display :global(h5:first-child),
  .content-display :global(h6:first-child) {
    margin-top: 0;
  }

  .content-display :global(ul),
  .content-display :global(ol) {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .content-display :global(li) {
    margin: var(--space-xs) 0;
    line-height: 1.5;
  }

  .content-display :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .content-display :global(em) {
    font-style: italic;
  }

  .content-display :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.9em;
  }

  .content-display :global(pre) {
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: var(--space-sm) 0;
  }

  .content-display :global(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--space-md);
    margin: var(--space-sm) 0;
    font-style: italic;
    color: var(--color-text-light);
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

  .completion-title {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
  }

  .loading-title {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    color: var(--color-text-light);
  }

  .small-spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid var(--color-primary);
    border-top: 2px solid transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
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

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-xl);
    gap: var(--space-md);
  }

  .error-message {
    color: var(--color-error);
    text-align: center;
    padding: var(--space-lg);
  }

  .retry-button {
    background-color: var(--color-primary);
    color: var(--color-surface);
    border: none;
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--border-radius);
    cursor: pointer;
    margin-top: var(--space-sm);
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

    .config-item,
    .warning-item {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-xs);
    }

    .completion-meta {
      grid-template-columns: 1fr;
    }
  }
</style>
