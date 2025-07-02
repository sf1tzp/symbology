<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type {
    FilingResponse,
    DocumentResponse,
    CompanyResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { formatDate, getFilingTypeLabel, getDocumentTypeName } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';

  const logger = getLogger('FilingDetail');
  const dispatch = createEventDispatcher<{
    documentSelected: DocumentResponse;
  }>();

  const { filing, company } = $props<{
    filing: FilingResponse;
    company?: CompanyResponse;
  }>();

  let documents = $state<DocumentResponse[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Fetch documents when filing changes
  $effect(() => {
    if (filing) {
      fetchDocuments();
    }
  });

  async function fetchDocuments() {
    loading = true;
    error = null;
    try {
      logger.debug('[FilingDetail] Fetching documents for filing', {
        filingId: filing.id,
        accessionNumber: filing.accession_number,
      });

      const filingDocuments = await fetchApi<DocumentResponse[]>(
        `/api/documents/by-filing/${filing.id}`
      );
      documents = filingDocuments;
      logger.debug('[FilingDetail] Fetched documents', { count: filingDocuments.length });
    } catch (err) {
      logger.error('[FilingDetail] Failed to fetch documents', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load documents';
      documents = [];
    } finally {
      loading = false;
    }
  }

  function handleDocumentClick(document: DocumentResponse) {
    logger.debug('[FilingDetail] Document selected', {
      documentId: document.id,
      documentName: document.document_name,
    });
    dispatch('documentSelected', document);
  }

  // Prepare filing meta items
  const filingMetaItems = $derived([
    { label: 'Filing Type', value: getFilingTypeLabel(filing.filing_type) },
    { label: 'Filing Date', value: formatDate(filing.filing_date) },
    ...(filing.period_of_report
      ? [{ label: 'Period of Report', value: formatDate(filing.period_of_report) }]
      : []),
    { label: 'Accession Number', value: filing.accession_number, mono: true },
    ...(filing.filing_url
      ? [{ label: 'SEC URL', value: 'Available', linkUrl: filing.filing_url }]
      : []),
  ]);

  // Prepare document meta items for each document
  function getDocumentMetaItems(document: DocumentResponse) {
    return [
      { label: 'Document Type', value: getDocumentTypeName(document.document_name) },
      { label: 'Document ID', value: document.id.substring(0, 8) + '...', mono: true },
    ];
  }

  // Prepare header display text
  const headerTitle = $derived(() => {
    const companyName = company?.display_name || company?.name || 'Company';
    const filingType = filing.filing_type;
    const periodEnd = filing.period_of_report ? formatDate(filing.period_of_report) : null;

    if (periodEnd) {
      return `${companyName} ${filingType} for period ending ${periodEnd}`;
    } else {
      return `${companyName} ${filingType}`;
    }
  });
</script>

<div class="filing-detail card">
  <header class="filing-header">
    <h1>{headerTitle()}</h1>
    <div class="filing-meta">
      <span class="filing-type-badge">{getFilingTypeLabel(filing.filing_type)}</span>
      <span class="filing-date">{formatDate(filing.filing_date)}</span>
    </div>
  </header>

  <section class="filing-summary">
    <h2>Filing Information</h2>
    <MetaItems items={filingMetaItems} />

    {#if filing.filing_url}
      <div class="sec-link-section">
        <a href={filing.filing_url} target="_blank" rel="noopener noreferrer" class="sec-link">
          📄 View Original SEC Filing
        </a>
      </div>
    {/if}
  </section>

  <section class="documents-section">
    <h2>Filing Documents</h2>

    {#if loading}
      <LoadingState message="Loading documents..." />
    {:else if error}
      <ErrorState message="Error loading documents: {error}" onRetry={fetchDocuments} />
    {:else if documents.length > 0}
      <div class="documents-list">
        {#each documents as document (document.id)}
          <div
            class="document-item"
            role="button"
            tabindex="0"
            onclick={() => handleDocumentClick(document)}
            onkeydown={(e) => e.key === 'Enter' && handleDocumentClick(document)}
          >
            <div class="document-header">
              <h3 class="document-title">{getDocumentTypeName(document.document_name)}</h3>
              <span class="document-name">{document.document_name}</span>
            </div>

            <MetaItems items={getDocumentMetaItems(document)} columns={2} variant="surface" />

            {#if document.content}
              <div class="document-preview">
                <span class="preview-text">
                  {document.content.substring(0, 200).trim()}...
                </span>
              </div>
            {/if}

            <div class="document-actions">
              <span class="action-hint">Click to view full document</span>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="no-documents">
        <p>No documents found for this filing.</p>
      </div>
    {/if}
  </section>
</div>

<style>
  .filing-detail {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  .filing-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
  }

  .filing-meta {
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

  .filing-summary h2,
  .documents-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .sec-link-section {
    margin-top: var(--space-md);
    text-align: center;
  }

  .sec-link {
    display: inline-block;
    background-color: var(--color-primary);
    color: var(--color-surface);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--border-radius);
    text-decoration: none;
    font-weight: var(--font-weight-bold);
    transition: background-color 0.2s ease;
  }

  .sec-link:hover {
    background-color: var(--color-primary-dark, var(--color-primary));
    transform: translateY(-1px);
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .document-item {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition:
      transform 0.2s ease,
      box-shadow 0.2s ease;
    cursor: pointer;
  }

  .document-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
  }

  .document-header {
    margin-bottom: var(--space-sm);
  }

  .document-title {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.1rem;
    font-weight: var(--font-weight-bold);
  }

  .document-name {
    display: block;
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin-top: var(--space-xs);
  }

  .document-preview {
    margin: var(--space-md) 0;
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .preview-text {
    color: var(--color-text);
    line-height: 1.5;
    font-size: 0.9rem;
  }

  .document-actions {
    margin-top: var(--space-sm);
    text-align: center;
  }

  .action-hint {
    font-size: 0.8rem;
    color: var(--color-text-light);
    font-style: italic;
  }

  .no-documents {
    color: var(--color-text-light);
    font-style: italic;
    margin: 0;
    padding: var(--space-md);
    text-align: center;
  }

  @media (max-width: 768px) {
    .filing-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }

    .documents-list {
      gap: var(--space-sm);
    }
  }
</style>
