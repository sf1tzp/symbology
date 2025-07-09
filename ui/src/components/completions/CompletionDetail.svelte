<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type {
    CompletionResponse,
    DocumentResponse,
    CompanyResponse,
    FilingResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import {
    formatDate,
    cleanContent,
    getDocumentTypeName,
    formatYear,
    formatTitleCase,
  } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import ModelConfig from '$components/ui/ModelConfig.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import BackButton from '$components/ui/BackButton.svelte';
  import appState, { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('CompletionDetail');
  const dispatch = createEventDispatcher<{
    documentSelected: DocumentResponse;
  }>();

  const { completion, company, filing } = $props<{
    completion: CompletionResponse;
    company?: CompanyResponse;
    filing?: FilingResponse;
  }>();

  let sourceDocuments = $state<DocumentResponse[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let showDetails = $state(false);

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

  // Create dynamic header title based on available context
  const headerTitle = $derived(() => {
    // Use props first, then fall back to app state
    const companyName =
      company?.display_name ||
      company?.name ||
      appState.selectedCompany?.display_name ||
      appState.selectedCompany?.name;
    let filingInfo = filing || appState.selectedFiling;

    // If no filing available but we have source documents, try to get filing from first document
    if (!filingInfo && sourceDocuments.length > 0) {
      const firstDocWithFiling = sourceDocuments.find((doc) => doc.filing);
      if (firstDocWithFiling?.filing) {
        filingInfo = firstDocWithFiling.filing;
      }
    }

    // Try to extract document type from source documents
    const documentTypes = sourceDocuments
      .map((doc) => getDocumentTypeName(doc.document_name))
      .filter((type, index, array) => array.indexOf(type) === index) // Remove duplicates
      .slice(0, 2); // Limit to first 2 types

    // Build title components
    const titleParts = [];

    if (companyName) {
      titleParts.push(`${formatTitleCase(companyName)}'s`);
    }

    if (filingInfo) {
      const fiscalYear = filingInfo.period_of_report
        ? formatYear(filingInfo.period_of_report)
        : null;
      if (fiscalYear) {
        titleParts.push(`${fiscalYear} ${filingInfo.filing_type}`);
      } else {
        titleParts.push(filingInfo.filing_type);
      }
    }

    if (documentTypes.length > 0) {
      titleParts.push(documentTypes.join(' & '));
    }

    // Default fallback
    if (titleParts.length === 0) {
      return 'Completion Analysis';
    }

    return `Analysis of ${titleParts.join(' ')} section`;
  });
</script>

<div class="card content-container">
  <header class="completion-header">
    <div class="header-top">
      <BackButton on:back={actions.navigateBack} />
      <h1>{headerTitle()}</h1>
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
        <span class="meta-item">Generated on {formatDate(completion.created_at)}</span>
        <ModelConfig item={completion} showSystemPrompt={true} />

        <section class="section-container">
          <h3 class="section-title-small">Included Context:</h3>

          {#if loading}
            <LoadingState message="Loading source documents..." />
          {:else if error}
            <ErrorState
              message="Error loading source documents: {error}"
              onRetry={fetchSourceDocuments}
            />
          {:else if sourceDocuments.length > 0}
            <div class="list-container">
              {#each sourceDocuments as document (document.id)}
                <div
                  class="btn btn-item"
                  role="button"
                  tabindex="0"
                  onclick={() => handleDocumentClick(document)}
                  onkeydown={(e) => e.key === 'Enter' && handleDocumentClick(document)}
                >
                  <div class="source-header">
                    <h3>{document.document_name}</h3>
                    <span class="meta-item">Document</span>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-content">
              <p>No source documents found for this completion.</p>
            </div>
          {/if}
        </section>
      </div>
    </div>
  </section>

  <section class="section-container">
    {#if cleanContent(completion.content)}
      <div class="content-box">
        <MarkdownContent content={cleanContent(completion.content) || ''} />
      </div>
    {:else}
      <div class="no-content">
        <p>No content available for this completion.</p>
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

  .completion-header h1 {
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

  /* Removed unused h2 selectors */

  .no-content {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
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

  /* Removed unused .unimplemented selector */

  /* Removed unused .completion-meta media query */
</style>
