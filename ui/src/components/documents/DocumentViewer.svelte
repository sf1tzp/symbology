<script lang="ts">
  import type { DocumentResponse, CompletionResponse } from '$utils/generated-api-types';
  import { getLogger } from '$utils/logger';
  import config from '$utils/config';
  import { formatDate, formatModelName } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';

  const logger = getLogger('DocumentViewer');

  // Props - now accepts document object and completion for enhanced context
  const { document, completion } = $props<{
    document: DocumentResponse | undefined;
    completion: CompletionResponse | undefined;
  }>();

  // Using Svelte 5 runes
  let loading = $state(false);
  let error = $state<string | null>(null);
  let documentContent = $state<string | null>(null);

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
    return id.substring(0, 8) + '...';
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
      <h1>{document.document_name || 'Unnamed Document'}</h1>
      <div class="document-meta">
        {#if document.filing?.filing_type}
          <span class="filing-type-badge">{document.filing.filing_type}</span>
        {/if}
        {#if document.filing?.filing_date}
          <span class="filing-date">{formatDate(document.filing.filing_date)}</span>
        {/if}
      </div>
    </header>

    <section class="document-summary">
      <h2>Document Information</h2>

      <MetaItems items={documentMetaItems} />

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
    </section>

    {#if completion}
      <section class="context-section">
        <h2>Used in Completion</h2>
        <div class="completion-info">
          <div class="completion-meta">
            <span class="model-badge">{formatModelName(completion.model)}</span>
            <span class="created-date">{formatDate(completion.created_at)}</span>
          </div>

          <MetaItems
            items={[
              ...(completion.temperature
                ? [{ label: 'Temperature', value: completion.temperature }]
                : []),
              ...(completion.top_p ? [{ label: 'Top-p', value: completion.top_p }] : []),
              ...(completion.num_ctx ? [{ label: 'Context', value: completion.num_ctx }] : []),
            ]}
            variant="surface"
          />
        </div>
      </section>
    {/if}

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

  .document-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
  }

  .document-meta {
    display: flex;
    gap: var(--space-md);
    align-items: center;
    margin-top: var(--space-sm);
  }

  .filing-type-badge {
    background-color: var(--color-primary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.9rem;
  }

  .filing-date {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .document-summary h2,
  .context-section h2,
  .content-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
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

  .completion-info {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .completion-meta {
    display: flex;
    gap: var(--space-md);
    align-items: center;
    margin-bottom: var(--space-md);
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

  @media (max-width: 768px) {
    .document-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }

    .completion-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
