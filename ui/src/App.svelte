<script lang="ts">
  import { getLogger } from '$utils/logger';
  import CompanySelector from '$components/company/CompanySelector.svelte';
  import AggregateSelector from '$components/aggregates/AggregateSelector.svelte';
  import CompletionSelector from '$components/completions/CompletionSelector.svelte';
  import DocumentViewer from '$components/documents/DocumentViewer.svelte';
  import PlaceholderCard from '$components/ui/PlaceholderCard.svelte';
  import CompanyDetail from '$components/company/CompanyDetail.svelte';
  import AggregateDetail from '$components/aggregates/AggregateDetail.svelte';
  import CompletionDetail from '$components/completions/CompletionDetail.svelte';
  import type {
    CompanyResponse,
    AggregateResponse,
    CompletionResponse,
  } from '$utils/generated-api-types';
  const logger = getLogger('App');

  let selectedCompany = $state<CompanyResponse | undefined>(undefined);
  let selectedAggregate = $state<AggregateResponse | undefined>(undefined);
  let selectedCompletion = $state<CompletionResponse | undefined>(undefined);
  let selectedDocumentId = $state<string | undefined>(undefined);

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

  // Effect to reset downstream selections when company changes
  $effect(() => {
    logger.debug('[App] Effect watching selectedCompany triggered', { selectedCompany });
    if (selectedCompany === undefined) {
      logger.debug(
        '[App] Clearing selectedAggregate, selectedCompletion, and selectedDocumentId because selectedCompany is undefined'
      );
      selectedAggregate = undefined;
      selectedCompletion = undefined;
      selectedDocumentId = undefined;
    }
  });

  // Effect to reset downstream selections when aggregate changes
  $effect(() => {
    logger.debug('[App] Effect watching selectedAggregate triggered', { selectedAggregate });
    if (selectedAggregate === undefined) {
      logger.debug(
        '[App] Clearing selectedCompletion and selectedDocumentId because selectedAggregate is undefined'
      );
      selectedCompletion = undefined;
      selectedDocumentId = undefined;
    }
  });

  // Effect to reset document selection when completion changes
  $effect(() => {
    logger.debug('[App] Effect watching selectedCompletion triggered', { selectedCompletion });
    if (selectedCompletion === undefined) {
      logger.debug('[App] Clearing selectedDocumentId because selectedCompletion is undefined');
      selectedDocumentId = undefined;
    }
    // Removed auto-selection of first document - let user choose from CompletionDetail
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

  // Event handlers
  function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
    selectedCompany = event.detail;
    selectedAggregate = undefined;
    selectedCompletion = undefined;
    selectedDocumentId = undefined;
  }

  function handleCompanyCleared() {
    logger.debug('[App] Company cleared event received, clearing all selections');
    selectedCompany = undefined;
    selectedAggregate = undefined;
    selectedCompletion = undefined;
    selectedDocumentId = undefined;
  }

  function handleAggregateSelected(event: CustomEvent<AggregateResponse>) {
    selectedAggregate = event.detail;
    selectedCompletion = undefined;
    selectedDocumentId = undefined;
  }

  function handleCompletionSelected(event: CustomEvent<CompletionResponse>) {
    selectedCompletion = event.detail;
    // selectedDocumentId will be set when user selects a document from CompletionDetail
  }

  function handleAggregateSelectedFromCompanyDetail(event: CustomEvent<AggregateResponse>) {
    selectedAggregate = event.detail;
    selectedCompletion = undefined;
    selectedDocumentId = undefined;
  }

  function handleDocumentSelected(event: CustomEvent<string>) {
    selectedDocumentId = event.detail;
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

  <div class="dashboard">
    <!-- Selectors row - now uses the streamlined flow -->
    <div class="selectors">
      <CompanySelector
        on:companySelected={handleCompanySelected}
        on:companyCleared={handleCompanyCleared}
      />
      <!-- <AggregateSelector company={selectedCompany} on:aggregateSelected={handleAggregateSelected} /> -->
      <!-- <CompletionSelector -->
      <!--   aggregate={selectedAggregate} -->
      <!--   on:completionSelected={handleCompletionSelected} -->
      <!-- /> -->
    </div>

    <!-- Content area with conditional layout -->
    <div class="content-area">
      {#if selectedCompany && !selectedAggregate}
        <!-- Show company detail when company selected but no aggregate -->
        <CompanyDetail
          company={selectedCompany}
          on:aggregateSelected={handleAggregateSelectedFromCompanyDetail}
        />
      {:else if selectedAggregate && !selectedCompletion}
        <!-- Show aggregate detail when aggregate selected but no completion -->
        <AggregateDetail
          aggregate={selectedAggregate}
          on:completionSelected={handleCompletionSelected}
        />
      {:else if selectedCompletion && !selectedDocumentId}
        <!-- Show completion detail when completion selected but no document -->
        <CompletionDetail
          completion={selectedCompletion}
          on:documentSelected={handleDocumentSelected}
        />
      {:else if selectedDocumentId}
        <!-- Show document viewer when we have a document -->
        <DocumentViewer documentId={selectedDocumentId} completion={selectedCompletion} />
      {:else}
        <!-- Show analysis panel as placeholder -->
        <PlaceholderCard completion={selectedCompletion} />
      {/if}
    </div>
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

  .selectors {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    z-index: 100;
  }

  .content-area {
    height: calc(100vh - 150px);
  }

  @media (min-width: 768px) {
    .dashboard {
      flex-direction: row;
    }

    .dashboard .selectors {
      width: 30%;
      max-width: 350px;
    }

    .dashboard .content-area {
      width: 70%;
      flex-grow: 1;
    }
  }
</style>
