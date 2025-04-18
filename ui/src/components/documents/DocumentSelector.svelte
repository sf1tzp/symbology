<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type { DocumentResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

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

  // New state variables for collapsible behavior
  let isListCollapsed = $state(false);
  let hoverTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on destroy
  onDestroy(() => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
  });

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
      isListCollapsed = false; // Reset collapsed state when filing changes
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

    // Collapse the documents list when a document is selected
    if (document) {
      isListCollapsed = true;
    }
  }

  // Functions to handle mouse events for expanding the list
  function handleMouseEnter() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (isListCollapsed && selectedDocument) {
      isListCollapsed = false;
    }
  }

  function handleMouseLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    if (selectedDocument && !loading) {
      // Add a small delay before collapsing to prevent jumpy UI
      hoverTimeout = setTimeout(() => {
        isListCollapsed = true;
      }, 300);
    }
  }

  // Function to handle focus events for accessibility
  function handleFocus() {
    if (isListCollapsed && selectedDocument) {
      isListCollapsed = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent, document: DocumentResponse) {
    // Select the document when Enter or Space is pressed
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectDocument(document);
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="document-selector card collapsible-component"
  class:has-selected={selectedDocument !== null}
  class:is-collapsed={isListCollapsed}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  onfocusin={handleFocus}
>
  <h2 class="collapsible-heading" class:is-collapsed={isListCollapsed}>Documents</h2>

  {#if !filingId}
    <p class="placeholder">Please select a filing to view its documents</p>
  {:else if loading}
    <p>Loading documents...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if documents.length === 0}
    <p>No documents found for this filing</p>
  {:else}
    <!-- Show documents list -->
    <div class="documents-container">
      <!-- Selected document is always visible -->
      {#if selectedDocument}
        <div class="document-item selected-item" tabindex="0" role="option" aria-selected={true}>
          <h3>{selectedDocument.document_name || 'Unnamed Document'}</h3>
        </div>
      {/if}

      <!-- Other documents (collapsible) -->
      <div
        class="documents-list scrollable collapsible-content"
        class:is-collapsed={isListCollapsed}
        role="listbox"
        aria-label="Documents list"
      >
        {#each documents as document}
          <!-- Skip selected document since it's already shown above -->
          {#if document.id !== selectedDocument?.id}
            <div
              class="document-item hover-lift"
              onclick={() => selectDocument(document)}
              onkeydown={(e) => handleKeyDown(e, document)}
              tabindex="0"
              role="option"
              aria-selected={false}
            >
              <h3>{document.document_name || 'Unnamed Document'}</h3>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .document-selector {
    position: relative;
    min-height: 50px;
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
  }

  .placeholder {
    color: var(--color-text-light);
    font-style: italic;
  }

  /* New container to organize the layout */
  .documents-container {
    display: flex;
    flex-direction: column;
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    margin-top: var(--space-md);
    max-height: 300px;
  }

  /* When collapsed, reduce height and fade out */
  .documents-list.is-collapsed {
    margin-top: 0;
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

  .document-item.selected-item {
    cursor: default;
    margin-bottom: var(--space-sm);
  }

  .document-item h3 {
    margin: 0;
    color: var(--color-text);
  }

  .error {
    color: var(--color-error);
  }

  /* Additional styles for collapsible behavior */
  .collapsible-component.has-selected.is-collapsed .collapsible-heading {
    margin-bottom: 0;
  }

  .collapsible-content.is-collapsed {
    max-height: 0;
    overflow: hidden;
    opacity: 0;
  }

  .collapsible-heading.is-collapsed {
    margin-bottom: 0;
  }

  .hover-lift:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
</style>
