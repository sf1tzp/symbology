<script lang="ts">
  import { onMount } from 'svelte';
  import DOMPurify from 'dompurify';
  import { getLogger } from '$utils/logger';

  const logger = getLogger('DocumentViewer');

  let documentContent = '';
  let loading = false;
  let error = null;
  let selectedDocument = null;

  // Function declarations moved to module scope
  function handleDocumentSelected(event) {
    selectedDocument = event.detail;
    if (selectedDocument) {
      loadDocumentContent(selectedDocument.id);
    } else {
      documentContent = '';
    }
  }

  async function loadDocumentContent(documentId) {
    try {
      loading = true;
      documentContent = '';
      const response = await fetch(`/api/documents/${documentId}/content`);
      if (!response.ok) throw new Error('Failed to fetch document content');
      const data = await response.json();
      documentContent = data.content || '';
    } catch (err) {
      error = err.message;
      logger.error('Error fetching document content:', err);
    } finally {
      loading = false;
    }
  }

  // Sanitize HTML content to prevent XSS attacks
  function sanitizeHtml(html) {
    // Configure DOMPurify with strict options
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p',
        'b',
        'i',
        'em',
        'strong',
        'a',
        'ul',
        'ol',
        'li',
        'br',
        'span',
        'div',
        'table',
        'tr',
        'td',
        'th',
        'thead',
        'tbody',
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'style'],
      FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
      FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
      SANITIZE_DOM: true,
      KEEP_CONTENT: true,
    });
  }

  // Listen for document selection events
  onMount(() => {
    window.addEventListener('document-selected', handleDocumentSelected);
    return () => {
      window.removeEventListener('document-selected', handleDocumentSelected);
    };
  });
</script>

/* eslint-disable svelte/no-at-html-tags */ /* eslint-disable no-inner-declarations */
<div class="document-viewer">
  <h2>Document Viewer</h2>

  {#if !selectedDocument}
    <p class="placeholder">Select a document to view its content</p>
  {:else if loading}
    <p>Loading document content...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if !documentContent}
    <p>No content available for this document</p>
  {:else}
    <div class="document-title">
      <h3>
        {selectedDocument.title || 'Document ' + selectedDocument.id}
      </h3>
    </div>
    <!-- Add suppression comment to acknowledge we're safely using DOMPurify -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="document-content">
      {@html sanitizeHtml(documentContent)}
    </div>
  {/if}
</div>

<style>
  .document-viewer {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 1rem;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .error {
    color: red;
  }

  .placeholder {
    color: #888;
    font-style: italic;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
  }

  .document-title {
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
  }

  .document-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    background-color: #f9f9f9;
    border-radius: 4px;
    line-height: 1.6;
  }
</style>
