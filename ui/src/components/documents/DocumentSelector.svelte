<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { DocumentResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    documentSelected: DocumentResponse;
  }>();
  const logger = getLogger('DocumentSelector');

  // Props
  const { filingId } = $props<{ filingId: string | undefined }>();

  // Using Svelte 5 runes
  let documents = $state<DocumentResponse[]>([]);
  let selectedDocument = $state<DocumentResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Watch for changes in filingId and fetch documents
  $effect(() => {
    logger.debug('[DocumentSelector] Effect watching filingId triggered', { filingId });
    if (filingId) {
      fetchDocuments();
    } else {
      logger.debug(
        '[DocumentSelector] Clearing documents and selectedDocument because filingId is undefined'
      );
      documents = [];
      selectedDocument = null;
    }
  });

  async function fetchDocuments() {
    if (!filingId) {
      error = 'No filing selected';
      return;
    }

    try {
      loading = true;
      error = null;
      documents = await fetchApi<DocumentResponse[]>(
        `${config.api.baseUrl}/filings/${filingId}/documents`
      );
      selectedDocument = null;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      logger.error('Error fetching documents:', err);
      documents = [];
    } finally {
      loading = false;
    }
  }

  function selectDocument(document: DocumentResponse) {
    selectedDocument = document;
    dispatch('documentSelected', document);
  }

  function handleKeyDown(event: KeyboardEvent, document: DocumentResponse) {
    // Select the document when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectDocument(document);
    }
  }
</script>

<div class="document-selector card">
  <h2>Documents</h2>

  {#if !filingId}
    <p class="placeholder">Please select a filing to view its documents</p>
  {:else if loading}
    <p>Loading documents...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if documents.length === 0}
    <p>No documents found for this filing</p>
  {:else}
    <div class="documents-list scrollable" role="listbox" aria-label="Documents list">
      {#each documents as document}
        <div
          class="document-item {selectedDocument?.id === document.id ? 'selected' : ''}"
          onclick={() => selectDocument(document)}
          onkeydown={(e) => handleKeyDown(e, document)}
          tabindex="0"
          role="option"
          aria-selected={selectedDocument?.id === document.id}
        >
          <h3>{document.document_name || 'Unnamed Document'}</h3>
        </div>
      {/each}
    </div>
  {/if}

  {#if selectedDocument && filingId}
    <div class="selected-document-info">
      <h3>Selected: {selectedDocument.document_name || 'Unnamed Document'}</h3>
    </div>
  {/if}
</div>

<style>
  .document-selector {
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .placeholder {
    color: var(--color-text-light);
    font-style: italic;
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    margin-top: var(--space-md);
    max-height: 300px;
  }

  .document-item {
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid var(--color-border);
  }

  .document-item:hover {
    border-color: var(--color-primary);
  }

  .document-item.selected {
    border-color: var(--color-primary);
    border-width: 2px;
    background-color: var(--color-surface);
  }

  .document-item h3 {
    margin: 0;
    color: var(--color-text);
  }

  .error {
    color: var(--color-error);
  }
</style>
