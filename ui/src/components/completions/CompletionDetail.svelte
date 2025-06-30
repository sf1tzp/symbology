<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { CompletionResponse, DocumentResponse } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { marked } from 'marked';

  const logger = getLogger('CompletionDetail');
  const dispatch = createEventDispatcher<{
    documentSelected: string;
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

  function handleDocumentClick(documentId: string) {
    logger.debug('[CompletionDetail] Document selected', { documentId });
    dispatch('documentSelected', documentId);
  }

  function formatDate(dateString: string | undefined) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  }

  function cleanCompletionContent(content: string | undefined): string | undefined {
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

  function getDocumentTypeName(docName: string): string {
    // Extract meaningful name from document names like "10-K Annual Report - Risk Factors"
    if (docName.toLowerCase().includes('risk')) return 'Risk Factors';
    if (docName.toLowerCase().includes('mda') || docName.toLowerCase().includes('management'))
      return 'Management Discussion & Analysis';
    if (docName.toLowerCase().includes('description') || docName.toLowerCase().includes('business'))
      return 'Business Description';
    return docName;
  }
</script>

<div class="completion-detail card">
  <header class="completion-header">
    <h1>Completion Overview</h1>
    <div class="completion-meta">
      <span class="model-badge">{completion.model.replace('_', ' ').toUpperCase()}</span>
      <span class="created-date">{formatDate(completion.created_at)}</span>
    </div>
  </header>

  <section class="summary-section">
    <h2>Summary</h2>

    <div class="model-config">
      <h3>Model Configuration</h3>
      <div class="config-grid">
        <div class="config-item">
          <span class="label">Model:</span>
          <span>{completion.model.replace('_', ' ').toUpperCase()}</span>
        </div>
        {#if completion.temperature !== null && completion.temperature !== undefined}
          <div class="config-item">
            <span class="label">Temperature:</span>
            <span>{completion.temperature}</span>
          </div>
        {/if}
        {#if completion.top_p !== null && completion.top_p !== undefined}
          <div class="config-item">
            <span class="label">Top-p:</span>
            <span>{completion.top_p}</span>
          </div>
        {/if}
        {#if completion.num_ctx !== null && completion.num_ctx !== undefined}
          <div class="config-item">
            <span class="label">Context Window:</span>
            <span>{completion.num_ctx.toLocaleString()}</span>
          </div>
        {/if}
        {#if completion.total_duration !== null && completion.total_duration !== undefined}
          <div class="config-item">
            <span class="label">Duration:</span>
            <span>{completion.total_duration.toFixed(2)}s</span>
          </div>
        {/if}
      </div>
    </div>

    {#if completion.system_prompt_id}
      <div class="response-warnings">
        <h3>Response Information</h3>
        <div class="warning-item">
          <span class="label">System Prompt ID:</span>
          <span class="mono">{completion.system_prompt_id}</span>
        </div>
      </div>
    {/if}
  </section>

  <section class="content-section">
    <h2>Content</h2>
    {#if cleanCompletionContent(completion.content)}
      <div class="content-display">
        {@html renderMarkdown(cleanCompletionContent(completion.content) || '')}
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
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <p>Loading source documents...</p>
      </div>
    {:else if error}
      <div class="error-message">
        <p>Error loading source documents: {error}</p>
        <button onclick={fetchSourceDocuments} class="retry-button">Retry</button>
      </div>
    {:else if sourceDocuments.length > 0}
      <div class="sources-list">
        {#each sourceDocuments as document}
          <div
            class="source-item"
            role="button"
            tabindex="0"
            onclick={() => handleDocumentClick(document.id)}
            onkeydown={(e) => e.key === 'Enter' && handleDocumentClick(document.id)}
          >
            <div class="source-header">
              <h3>{getDocumentTypeName(document.document_name)}</h3>
              <span class="source-type">Document</span>
            </div>

            <div class="source-meta">
              <div class="meta-item">
                <span class="label">Document Name:</span>
                <span class="document-name">{document.document_name}</span>
              </div>
              {#if document.filing_id}
                <div class="meta-item">
                  <span class="label">Filing ID:</span>
                  <span class="mono">{document.filing_id}</span>
                </div>
              {/if}
            </div>

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

  .source-meta {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  .meta-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .meta-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    font-size: 0.9rem;
    flex-shrink: 0;
    margin-right: var(--space-sm);
  }

  .meta-item .document-name {
    color: var(--color-text-light);
    font-size: 0.9rem;
    text-align: right;
    word-break: break-word;
  }

  .meta-item span:not(.label):not(.document-name) {
    color: var(--color-text-light);
    font-family: monospace;
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
  }

  .source-preview p {
    margin: 0;
    font-size: 0.9rem;
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
    .completion-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }

    .config-item,
    .warning-item,
    .meta-item {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-xs);
    }
  }
</style>
