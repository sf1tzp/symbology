<script lang="ts">
  import type { DocumentResponse, CompletionResponse } from '$utils/generated-api-types';
  import { getLogger } from '$utils/logger';
  import config from '$utils/config';
  import { marked } from 'marked';

  const logger = getLogger('DocumentViewer');

  // Props - now accepts both document ID and completion for enhanced context
  const { documentId, completion } = $props<{
    documentId: string | undefined;
    completion: CompletionResponse | undefined;
  }>();

  // Using Svelte 5 runes
  let loading = $state(false);
  let error = $state<string | null>(null);
  let document = $state<DocumentResponse | null>(null);
  let documentContent = $state<string | null>(null);

  // Watch for changes in documentId and fetch document
  $effect(() => {
    logger.debug('[DocumentViewer] Effect watching documentId triggered', { documentId });
    if (documentId) {
      fetchDocument();
    } else {
      logger.debug('[DocumentViewer] Clearing document because documentId is undefined');
      error = null;
      document = null;
      documentContent = null;
    }
  });

  async function fetchDocument() {
    if (!documentId) return;

    try {
      loading = true;
      error = null;

      // Fetch document metadata (now includes filing information)
      const docResponse = await fetch(`${config.api.baseUrl}/documents/${documentId}`);
      if (!docResponse.ok) {
        throw new Error(`Failed to fetch document: ${docResponse.statusText}`);
      }
      document = await docResponse.json();

      // Fetch document content
      const contentResponse = await fetch(`${config.api.baseUrl}/documents/${documentId}/content`);
      if (!contentResponse.ok) {
        throw new Error(`Failed to fetch document content: ${contentResponse.statusText}`);
      }
      documentContent = await contentResponse.text();

      logger.debug('[DocumentViewer] Document loaded', {
        documentId,
        documentName: document?.document_name,
        contentLength: documentContent?.length,
        hasFilingUrl: !!document?.filing?.filing_url,
      });
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching document:', err);
    } finally {
      loading = false;
    }
  }

  // Helper function to format model name for display
  function formatModelName(model: string): string {
    return model.replace('_', ' ').toUpperCase();
  }

  // Helper function to format document ID for display
  function formatDocumentId(id: string): string {
    return id.substring(0, 8) + '...';
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

<div class="document-viewer card">
  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading document...</p>
    </div>
  {:else if error}
    <div class="error-container">
      <p class="error-message">Error: {error}</p>
    </div>
  {:else if !documentId}
    <div class="placeholder-container">
      <div class="placeholder-content">
        <h3>Document Viewer</h3>
        <p class="placeholder">Select a document to view its content</p>
      </div>
    </div>
  {:else if document}
    <div class="document-header">
      <div class="title-section">
        <h2>{document.document_name || 'Unnamed Document'}</h2>
        <p class="document-id">ID: {formatDocumentId(document.id)}</p>
      </div>

      {#if document.filing?.filing_url}
        <div class="source-links">
          <a
            href={document.filing.filing_url}
            target="_blank"
            rel="noopener noreferrer"
            class="sec-link"
          >
            📄 View Original SEC Filing
          </a>
          {#if document.filing.filing_type}
            <span class="filing-info">
              {document.filing.filing_type} • {new Date(
                document.filing.filing_date
              ).toLocaleDateString()}
            </span>
          {/if}
        </div>
      {/if}

      {#if completion}
        <div class="context-section">
          <h4>Used in Completion</h4>
          <p class="completion-info">
            Model: <strong>{formatModelName(completion.model)}</strong>
          </p>
          {#if completion.temperature}
            <p class="config-detail">Temperature: {completion.temperature}</p>
          {/if}
          <p class="timestamp">
            Created: {new Date(completion.created_at).toLocaleDateString()}
          </p>
        </div>
      {/if}
    </div>

    <div class="document-content scrollable">
      {#if documentContent}
        <div class="content-wrapper">
          <div class="document-markdown">
            {@html renderMarkdown(documentContent)}
          </div>
        </div>
      {:else}
        <p class="no-content">No content available for this document</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .document-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .placeholder-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-lg);
  }

  .placeholder-content {
    text-align: center;
  }

  .placeholder-content h3 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
  }

  .placeholder {
    font-style: italic;
    color: var(--color-text-light);
    margin: 0;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: var(--space-md);
  }

  .error-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-lg);
  }

  .document-header {
    padding: var(--space-lg);
    border-bottom: 1px solid var(--color-border);
    background-color: var(--color-surface);
  }

  .title-section {
    margin-bottom: var(--space-md);
  }

  .title-section h2 {
    margin: 0 0 var(--space-xs) 0;
    color: var(--color-text);
    font-size: 1.3rem;
  }

  .document-id {
    margin: 0;
    font-family: monospace;
    font-size: 0.9rem;
    color: var(--color-text-light);
  }

  .context-section {
    margin-bottom: var(--space-md);
    padding: var(--space-md);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .context-section h4 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-size: 0.95rem;
  }

  .completion-info {
    margin: 0 0 var(--space-xs) 0;
    font-size: 0.9rem;
    color: var(--color-text);
  }

  .config-detail {
    margin: 0 0 var(--space-xs) 0;
    font-size: 0.8rem;
    color: var(--color-text-light);
    font-family: monospace;
  }

  .timestamp {
    margin: 0;
    font-size: 0.8rem;
    color: var(--color-text-light);
  }

  .source-links {
    margin-top: var(--space-md);
  }

  .sec-link {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-sm) var(--space-md);
    background-color: var(--color-primary);
    color: white;
    text-decoration: none;
    border-radius: var(--border-radius);
    font-size: 0.9rem;
    font-weight: 500;
    transition: background-color 0.2s ease;
  }

  .sec-link:hover {
    background-color: var(--color-primary-hover);
  }

  .filing-info {
    display: inline-block;
    margin-left: var(--space-md);
    font-size: 0.8rem;
    color: var(--color-text-light);
    font-style: italic;
  }

  .document-content {
    flex: 1;
    overflow-y: auto;
    padding: 0;
  }

  .content-wrapper {
    padding: var(--space-lg);
  }

  .document-markdown {
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
    font-family: var(--font-family-body);
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--color-text);
    background-color: transparent;
  }

  .document-markdown :global(p) {
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.6;
    color: var(--color-text);
  }

  .document-markdown :global(p:last-child) {
    margin-bottom: 0;
  }

  .document-markdown :global(h1),
  .document-markdown :global(h2),
  .document-markdown :global(h3),
  .document-markdown :global(h4),
  .document-markdown :global(h5),
  .document-markdown :global(h6) {
    margin: var(--space-lg) 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
  }

  .document-markdown :global(h1:first-child),
  .document-markdown :global(h2:first-child),
  .document-markdown :global(h3:first-child),
  .document-markdown :global(h4:first-child),
  .document-markdown :global(h5:first-child),
  .document-markdown :global(h6:first-child) {
    margin-top: 0;
  }

  .document-markdown :global(h1) {
    font-size: 1.8rem;
    border-bottom: 2px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .document-markdown :global(h2) {
    font-size: 1.5rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-xs);
  }

  .document-markdown :global(h3) {
    font-size: 1.3rem;
  }

  .document-markdown :global(h4) {
    font-size: 1.1rem;
  }

  .document-markdown :global(h5) {
    font-size: 1rem;
  }

  .document-markdown :global(h6) {
    font-size: 0.9rem;
  }

  .document-markdown :global(ul),
  .document-markdown :global(ol) {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .document-markdown :global(li) {
    margin: var(--space-xs) 0;
    line-height: 1.5;
  }

  .document-markdown :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .document-markdown :global(em) {
    font-style: italic;
  }

  .document-markdown :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.85em;
    border: 1px solid var(--color-border);
  }

  .document-markdown :global(pre) {
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: var(--space-md) 0;
    border: 1px solid var(--color-border);
  }

  .document-markdown :global(pre code) {
    background: none;
    padding: 0;
    border: none;
  }

  .document-markdown :global(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--space-md);
    margin: var(--space-md) 0;
    font-style: italic;
    color: var(--color-text-light);
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
  }

  .document-markdown :global(table) {
    border-collapse: collapse;
    width: 100%;
    margin: var(--space-md) 0;
    border: 1px solid var(--color-border);
  }

  .document-markdown :global(th),
  .document-markdown :global(td) {
    border: 1px solid var(--color-border);
    padding: var(--space-sm);
    text-align: left;
  }

  .document-markdown :global(th) {
    background-color: var(--color-surface);
    font-weight: var(--font-weight-bold);
  }

  .document-markdown :global(hr) {
    border: none;
    border-top: 2px solid var(--color-border);
    margin: var(--space-lg) 0;
  }

  .document-markdown :global(a) {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .document-markdown :global(a:hover) {
    color: var(--color-primary-hover);
  }

  .no-content {
    padding: var(--space-lg);
    text-align: center;
    font-style: italic;
    color: var(--color-text-light);
    margin: 0;
  }

  /* Loading spinner styles */
  .loading-spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--color-border);
    border-top: 3px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }
</style>
