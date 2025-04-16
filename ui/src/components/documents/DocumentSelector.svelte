<script lang="ts">
  import { onMount } from 'svelte';
  import { getLogger } from '$utils/logger';

  const logger = getLogger('DocumentSelector');

  let documents = [];
  let selectedDocument = null;
  let loading = false;
  let error = null;
  let selectedFiling = null;

  // Function declarations moved to module scope
  function handleFilingSelected(event) {
    selectedFiling = event.detail;
    selectedDocument = null;
    if (selectedFiling) {
      loadDocuments(selectedFiling.id);
    } else {
      documents = [];
    }
  }

  async function loadDocuments(filingId) {
    try {
      loading = true;
      documents = [];
      const response = await fetch(`/api/filings/${filingId}/documents`);
      if (!response.ok) throw new Error('Failed to fetch documents');
      documents = await response.json();
    } catch (err) {
      error = err.message;
      logger.error('Error fetching documents:', err);
    } finally {
      loading = false;
    }
  }

  function selectDocument(document) {
    selectedDocument = document;
    // Dispatch an event to notify parent components
    const event = new CustomEvent('document-selected', {
      detail: document,
    });
    window.dispatchEvent(event);
  }

  // Listen for filing selection events
  onMount(() => {
    window.addEventListener('filing-selected', handleFilingSelected);
    return () => {
      window.removeEventListener('filing-selected', handleFilingSelected);
    };
  });
</script>

/* eslint-disable no-inner-declarations */
<div class="documents-selector">
  <h2>Document Selector</h2>

  {#if !selectedFiling}
    <p>Please select a filing first</p>
  {:else if loading}
    <p>Loading documents...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if documents.length === 0}
    <p>No documents found for this filing</p>
  {:else}
    <ul class="documents-list">
      {#each documents as document}
        <li>
          <button
            class="document-item {selectedDocument && selectedDocument.id === document.id
              ? 'selected'
              : ''}"
            on:click={() => selectDocument(document)}
            type="button"
          >
            <div class="document-title">
              {document.title || 'Document ' + document.id}
            </div>
            <div class="document-type">
              {document.type || 'Unknown type'}
            </div>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .documents-selector {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .error {
    color: red;
  }

  .documents-list {
    max-height: 300px;
    overflow-y: auto;
    list-style: none;
    padding: 0;
    margin: 0;
  }

  li {
    margin-bottom: 0.25rem;
  }

  .document-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.5rem;
    border: 1px solid #eee;
    border-radius: 4px;
    cursor: pointer;
    background-color: white;
  }

  .document-item:hover {
    background-color: #f0f0f0;
  }

  .document-item.selected {
    background-color: #e0e0e0;
    border-color: #aaa;
  }

  .document-title {
    font-weight: bold;
  }

  .document-type {
    font-size: 0.9rem;
    color: #666;
  }
</style>
