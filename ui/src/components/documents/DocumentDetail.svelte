<script lang="ts">
  import type { DocumentResponse, CompletionResponse } from '$utils/generated-api-types';
  import { getLogger } from '$utils/logger';
  import { config } from '$utils/config';
  import { formatDate } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';
  import BackButton from '$components/ui/BackButton.svelte';
  import { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('DocumentDetail');

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
    logger.info('document_changed', { documentId: document?.id });
    if (document?.id) {
      fetchDocumentContent();
    } else {
      error = null;
      documentContent = null;
    }
  });

  async function fetchDocumentContent() {
    if (!document?.id) return;

    try {
      loading = true;
      error = null;

      logger.info('document_content_fetch_start', { documentId: document.id });

      // Fetch document content
      const contentResponse = await fetch(`${config.api.baseUrl}/documents/${document.id}/content`);
      if (!contentResponse.ok) {
        throw new Error(`Failed to fetch document content: ${contentResponse.statusText}`);
      }
      documentContent = await contentResponse.text();

      logger.info('document_content_fetch_success', {
        documentId: document.id,
        contentLength: documentContent?.length,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      error = errorMessage;
      logger.error('document_content_fetch_failed', {
        error: errorMessage,
        documentId: document?.id,
      });
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
  <div class="card content-container">
    <div class="placeholder-container">
      <div class="placeholder-content">
        <h3>Document Detail</h3>
        <p class="meta-item">Select a document to view its content</p>
      </div>
    </div>
  </div>
{:else}
  <div class="card content-container">
    <header class="document-header">
      <div class="header-top">
        <BackButton on:back={actions.navigateBack} />
        <h1>{document.document_name || 'Unnamed Document'}</h1>
      </div>
    </header>

    <section class="section-container">
      <div
        class="section-header"
        role="button"
        tabindex="0"
        onclick={() => (showDocumentInfo = !showDocumentInfo)}
        onkeydown={(e) => e.key === 'Enter' && (showDocumentInfo = !showDocumentInfo)}
        aria-label={showDocumentInfo ? 'Hide document info' : 'Show document info'}
      >
        <h2 class="section-title">Document Information</h2>
        <span class="icon" class:icon-collapsed={!showDocumentInfo}>▼</span>
      </div>

      <div class:collapsed={!showDocumentInfo}>
        <MetaItems items={documentMetaItems} />

        {#if document.filing}
          <div class="filing-actions">
            <button type="button" class="btn btn-action" onclick={viewFilingDetail}>
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
              class="btn btn-action"
            >
              📄 View Original SEC Filing
            </a>
          </div>
        {/if}
      </div>
    </section>

    <section class="section-container">
      <h2 class="section-title">Content</h2>
      {#if loading}
        <LoadingState message="Loading document content..." />
      {:else if error}
        <ErrorState message="Error: {error}" onRetry={fetchDocumentContent} />
      {:else if documentContent}
        <div class="content-box">
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

  .filing-actions,
  .source-links {
    margin-top: var(--space-md);
  }
</style>
