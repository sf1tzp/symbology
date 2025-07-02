<script lang="ts">
  import type { DocumentResponse, CompletionResponse } from '$utils/generated-api-types';
  import { getLogger } from '$utils/logger';
  import config from '$utils/config';
  import { formatDate } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';
  import BackButton from '$components/ui/BackButton.svelte';
  import { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('DocumentViewer');

  // Props - now accepts document object and completion for enhanced context
  const { document } = $props<{
    document: DocumentResponse | undefined;
    completion?: CompletionResponse | undefined;
  }>();

  // Using Svelte 5 runes
  let loading = $state(false);
  let error = $state<string | null>(null);
  let documentContent = $state<string | null>(null);
  let showDocumentInfo = $state(false);

  // Watch for changes in document and fetch content
  $effect(() => {
    logger.debug('[DocumentViewer] Effect watching document triggered', {
      documentId: document?.id,
      documentName: document?.document_name,
    });
    if (document?.id) {
      fetchDocumentContent();
    } else {
      logger.debug('[DocumentViewer] Clearing document content because document is undefined');
      error = null;
      documentContent = null;
    }
  });

  async function fetchDocumentContent() {
    if (!document?.id) return;

    try {
      loading = true;
      error = null;

      // Fetch document content
      const contentResponse = await fetch(`${config.api.baseUrl}/documents/${document.id}/content`);
      if (!contentResponse.ok) {
        throw new Error(`Failed to fetch document content: ${contentResponse.statusText}`);
      }
      documentContent = await contentResponse.text();

      logger.debug('[DocumentViewer] Document content loaded', {
        documentId: document.id,
        documentName: document.document_name,
        contentLength: documentContent?.length,
        hasFilingUrl: !!document.filing?.filing_url,
      });
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching document content:', err);
    } finally {
      loading = false;
    }
  }

  // Helper function to format document ID for display
  function formatDocumentId(id: string): string {
    return id;
  }

  // Navigate to filing detail view
  function viewFilingDetail() {
    if (document?.filing) {
      actions.selectFiling(document.filing);
    }
  }

  // Prepare document meta items
  const documentMetaItems = $derived(
    document
      ? [
          { label: 'Document ID', value: formatDocumentId(document.id), mono: true },
          ...(document.filing_id
            ? [{ label: 'Filing ID', value: document.filing_id, mono: true }]
            : []),
          ...(document.filing?.filing_type
            ? [{ label: 'Filing Type', value: document.filing.filing_type }]
            : []),
          ...(document.filing?.filing_date
            ? [{ label: 'Filed', value: formatDate(document.filing.filing_date) }]
            : []),
        ]
      : []
  );
</script>

{#if !document}
  <div class="document-viewer card">
    <div class="placeholder-container">
      <div class="placeholder-content">
        <h3>Document Viewer</h3>
        <p class="placeholder">Select a document to view its content</p>
      </div>
    </div>
  </div>
{:else}
  <div class="document-viewer card">
    <header class="document-header">
      <div class="header-top">
        <BackButton on:back={actions.navigateBack} />
        <h1>{document.document_name || 'Unnamed Document'}</h1>
      </div>
    </header>

    <section class="document-summary">
      <div
        class="section-header"
        role="button"
        tabindex="0"
        onclick={() => (showDocumentInfo = !showDocumentInfo)}
        onkeydown={(e) => e.key === 'Enter' && (showDocumentInfo = !showDocumentInfo)}
        aria-label={showDocumentInfo ? 'Hide document info' : 'Show document info'}
      >
        <h2>Document Information</h2>
        <span class="toggle-icon" class:collapsed={!showDocumentInfo}>▼</span>
      </div>

      {#if showDocumentInfo}
        <MetaItems items={documentMetaItems} />

        {#if document.filing}
          <div class="filing-actions">
            <button type="button" class="filing-link-btn" onclick={viewFilingDetail}>
              📋 View Filing Details
            </button>
          </div>
        {/if}

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
          </div>
        {/if}
      {/if}
    </section>

    <section class="content-section">
      <h2>Content</h2>
      {#if loading}
        <LoadingState message="Loading document content..." />
      {:else if error}
        <ErrorState message="Error: {error}" onRetry={fetchDocumentContent} />
      {:else if documentContent}
        <div class="content-display">
          <MarkdownContent content={documentContent} />
        </div>
      {:else}
        <div class="no-content">
          <p>No content available for this document</p>
        </div>
      {/if}
    </section>
  </div>
{/if}

<style>
  .document-viewer {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
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

  .header-top {
    display: flex;
    align-items: flex-start;
    gap: var(--space-md);
    margin-bottom: var(--space-sm);
  }

  .document-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
    flex: 1;
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

  .section-header:hover {
    background-color: var(--color-background);
  }

  .section-header:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .section-header h2 {
    margin: 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
    flex: 1;
    pointer-events: none;
  }

  .toggle-icon {
    display: inline-block;
    font-size: 0.8rem;
    color: var(--color-text-light);
    transition: transform 0.2s ease;
    pointer-events: none;
  }

  .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

  /* Removed unused h2 selectors */

  .source-links {
    margin-top: var(--space-md);
  }

  .filing-actions {
    margin-top: var(--space-md);
  }

  .filing-link-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-sm) var(--space-md);
    background-color: var(--color-secondary, #6366f1);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .filing-link-btn:hover {
    background-color: var(--color-secondary-hover, #4f46e5);
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

  /* Removed unused .completion-info selector */

  .content-display {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .no-content {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }
</style>
