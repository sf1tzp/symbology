<script lang="ts">
  import type { DocumentResponse } from '$utils/generated-api-types';
  import { getLogger } from '$utils/logger';
  import config from '$utils/config';

  const logger = getLogger('DocumentViewer');

  // Props
  const { document } = $props<{ document: DocumentResponse | null }>();

  // Using Svelte 5 runes
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Watch for changes in document and fetch content
  $effect(() => {
    if (document) {
      fetchDocumentContent(document.id);
    } else {
      error = null;
    }
  });

  async function fetchDocumentContent(documentId: number) {
    if (!documentId) return;

    try {
      loading = true;
      error = null;

      const response = await fetch(`${config.api.baseUrl}/documents/${documentId}/content`);
      if (!response.ok) {
        throw new Error(`Failed to fetch document content: ${response.statusText}`);
      }
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching document content:', err);
    } finally {
      loading = false;
    }
  }
</script>

<div class="document-viewer card">
  {#if !document}
    <p class="placeholder">Select a document to view its content</p>
  {:else if loading}
    <div class="loading">
      <p>Loading document content...</p>
    </div>
  {:else if error}
    <div class="error">
      <p>Error: {error}</p>
    </div>
  {:else}
    <div class="document-header">
      <h2>{document.document_name || 'Unnamed Document'}</h2>
      <p class="meta">Document ID: {document.id}</p>
    </div>
    <div class="document-content scrollable">
      <pre>{document.content}</pre>
    </div>
  {/if}
</div>

<style>
  .document-viewer {
    height: 95%;
    display: flex;
    flex-direction: column;
  }

  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-style: italic;
    color: var(--color-text-light);
  }

  .loading,
  .error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
  }

  .error {
    color: var(--color-error);
  }

  .document-header {
    padding: var(--space-md);
    border-bottom: 1px solid var(--color-border);
  }

  .document-header h2 {
    margin: 0 0 var(--space-xs) 0;
  }

  .meta {
    font-size: 0.8rem;
    color: var(--color-text-light);
    margin: 0;
  }

  .document-content {
    flex: 1;
    max-height: 70vh;
    padding: var(--space-md);
    border-top: 1px solid var(--color-border);
  }

  pre {
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
    font-family: monospace;
    font-size: 0.9rem;
    line-height: 1.5;
  }
</style>
