<script lang="ts">
  import { getLogger } from '$utils/logger';
  import CompanySelector from '$components/company/CompanySelector.svelte';
  import FilingsSelector from '$components/filings/FilingsSelector.svelte';
  import DocumentSelector from '$components/documents/DocumentSelector.svelte';
  import DocumentViewer from '$components/documents/DocumentViewer.svelte';
  import PlaceholderCard from '$components/ui/PlaceholderCard.svelte';
  import type {
    CompanyResponse,
    FilingResponse,
    DocumentResponse,
  } from '$utils/generated-api-types';
  const logger = getLogger('CompanySelector');

  let selectedCompany = $state<CompanyResponse | null>(null);
  let selectedFiling = $state<FilingResponse | null>(null);
  let selectedDocument = $state<DocumentResponse | null>(null);

  // Track if horizontal layout has ever been activated
  let hasActivatedHorizontalLayout = $state(false);

  // Derived state to check if all selections are made
  let allSelectionsReady = $derived(
    selectedCompany !== null && selectedFiling !== null && selectedDocument !== null
  );

  // Effect to "latch" the horizontal layout once all selections have been made
  $effect(() => {
    if (allSelectionsReady) {
      hasActivatedHorizontalLayout = true;
    }
  });

  // Theme state
  let isDarkMode = $state(window.matchMedia('(prefers-color-scheme: dark)').matches);
  let themeInitialized = $state(false);

  // Initialize theme from localStorage or system preference
  $effect(() => {
    if (!themeInitialized) {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        isDarkMode = savedTheme === 'dark';
      }
      applyTheme();
      themeInitialized = true;
    }
  });

  // Effect to reset filing and document when company becomes unset
  $effect(() => {
    logger.debug('[App] Effect watching selectedCompany triggered', { selectedCompany });
    if (selectedCompany === null) {
      logger.debug(
        '[App] Clearing selectedFiling and selectedDocument because selectedCompany is null'
      );
      selectedFiling = null;
      selectedDocument = null;
    }
  });

  // Apply theme changes
  function toggleTheme() {
    isDarkMode = !isDarkMode;
    applyTheme();
  }

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
  }

  // FIXME: If a company / filing / document are selected, we should stay there if the page refreshes
  function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
    selectedCompany = event.detail;
    selectedFiling = null;
    selectedDocument = null;
  }

  function handleCompanyCleared() {
    logger.debug('[App] Company cleared event received, clearing all selections');
    selectedCompany = null;
    selectedFiling = null;
    selectedDocument = null;
  }

  function handleFilingSelected(event: CustomEvent<FilingResponse>) {
    selectedFiling = event.detail;
    selectedDocument = null;
  }

  function handleDocumentSelected(event: CustomEvent<DocumentResponse>) {
    selectedDocument = event.detail;
  }
</script>

<main>
  <header class="header">
    <h1>Symbology</h1>
    <button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
      {#if isDarkMode}
        <span class="theme-icon">☀️</span>
        <span class="theme-label">Light Mode</span>
      {:else}
        <span class="theme-icon">🌙</span>
        <span class="theme-label">Dark Mode</span>
      {/if}
    </button>
  </header>

  <div class="dashboard" class:side-by-side-layout={hasActivatedHorizontalLayout}>
    <!-- Selectors row - always visible but changes layout based on selections -->
    <div class="selectors" class:selectors-horizontal={hasActivatedHorizontalLayout}>
      <CompanySelector
        on:companySelected={handleCompanySelected}
        on:companyCleared={handleCompanyCleared}
      />
      <FilingsSelector companyId={selectedCompany?.id} on:filingSelected={handleFilingSelected} />
      <DocumentSelector
        filingId={selectedFiling?.id}
        on:documentSelected={handleDocumentSelected}
      />
    </div>

    <!-- Content area with conditional layout -->
    {#if hasActivatedHorizontalLayout}
      <div class="content-area-split">
        <div class="content-panel">
          <DocumentViewer document={selectedDocument} />
        </div>
        <div class="content-panel">
          <PlaceholderCard />
        </div>
      </div>
    {:else}
      <div class="content-area">
        <DocumentViewer document={selectedDocument} />
      </div>
    {/if}
  </div>
</main>

<style>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-md);
    padding: var(--space-md);
    border-bottom: 1px solid var(--color-border);
  }

  .header h1 {
    margin: 0;
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
  }

  .theme-toggle {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    background-color: var(--color-surface);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-xs) var(--space-sm);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .theme-toggle:hover {
    border-color: var(--color-primary);
  }

  .theme-icon {
    font-size: 1.2rem;
  }

  @media (max-width: 600px) {
    .theme-label {
      display: none;
    }

    .theme-toggle {
      padding: var(--space-xs);
    }
  }

  .dashboard {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  /* Side-by-side layout specific styles */
  .side-by-side-layout {
    flex-direction: column;
  }

  .selectors {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    z-index: 100;
  }

  /* Horizontal selectors when all selections are made */
  .selectors-horizontal {
    flex-direction: row;
    justify-content: space-between;
    flex-wrap: wrap;
    z-index: 1000;
  }

  .selectors-horizontal :global(.card) {
    flex: 1;
    min-width: 250px;
    margin-right: var(--space-sm);
  }

  .selectors-horizontal :global(.card:last-child) {
    margin-right: 0;
  }

  .content-area {
    height: calc(100vh - 150px);
  }

  /* Split content area for side-by-side layout */
  .content-area-split {
    display: flex;
    flex-direction: row;
    gap: var(--space-md);
    height: calc(100vh - 350px);
  }

  .content-panel {
    flex: 1;
    min-width: 0; /* Allows proper flexbox shrinking */
    max-height: 100%;
  }

  @media (min-width: 768px) {
    .dashboard:not(.side-by-side-layout) {
      flex-direction: row;
    }

    .dashboard:not(.side-by-side-layout) .selectors {
      width: 30%;
      max-width: 350px;
    }

    .dashboard:not(.side-by-side-layout) .content-area {
      width: 70%;
      flex-grow: 1;
    }

    /* For small screens, revert to vertical layout even when all selections are made */
    @media (max-width: 1024px) {
      .side-by-side-layout .content-area-split {
        flex-direction: column;
        height: auto;
      }

      .side-by-side-layout .content-panel {
        height: calc(50vh - 150px);
      }
    }
  }
</style>
