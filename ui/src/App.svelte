<script lang="ts">
  import { getLogger } from '$utils/logger';
  import CompanySelector from '$components/company/CompanySelector.svelte';
  import DocumentViewer from '$components/documents/DocumentViewer.svelte';
  import PlaceholderCard from '$components/ui/PlaceholderCard.svelte';
  import CompanyDetail from '$components/company/CompanyDetail.svelte';
  import FilingDetail from '$components/filings/FilingDetail.svelte';
  import AggregateDetail from '$components/aggregates/AggregateDetail.svelte';
  import CompletionDetail from '$components/completions/CompletionDetail.svelte';
  import type {
    CompanyResponse,
    AggregateResponse,
    CompletionResponse,
    DocumentResponse,
    FilingResponse,
  } from '$utils/generated-api-types';
  import appState, { actions } from '$utils/state-manager.svelte';

  const logger = getLogger('App');

  // Theme state is now managed in the state manager
  let themeInitialized = $state(false);

  // Initialize theme from state manager
  $effect(() => {
    if (!themeInitialized) {
      actions.initializeTheme();
      themeInitialized = true;
    }
  });

  // Event handlers - now much simpler since state is managed centrally
  function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
    actions.selectCompany(event.detail);
  }

  function handleCompanyCleared() {
    logger.debug('[App] Company cleared event received, clearing all selections');
    actions.clearAll();
  }

  function handleCompletionSelected(event: CustomEvent<CompletionResponse>) {
    actions.selectCompletion(event.detail);
  }

  function handleAggregateSelectedFromCompanyDetail(event: CustomEvent<AggregateResponse>) {
    actions.selectAggregate(event.detail);
  }

  function handleFilingSelected(event: CustomEvent<FilingResponse>) {
    actions.selectFiling(event.detail);
  }

  function handleDocumentSelected(event: CustomEvent<DocumentResponse>) {
    actions.selectDocument(event.detail);
  }
</script>

<main>
  <header class="header">
    <h1>Symbology</h1>
    <button class="theme-toggle" onclick={actions.toggleTheme} aria-label="Toggle theme">
      {#if appState.isDarkMode}
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
      <!-- <AggregateSelector company={appState.selectedCompany} on:aggregateSelected={handleAggregateSelected} /> -->
      <!-- <CompletionSelector -->
      <!--   aggregate={appState.selectedAggregate} -->
      <!--   on:completionSelected={handleCompletionSelected} -->
      <!-- /> -->
    </div>

    <!-- Content area with conditional layout based on currentView derived state -->
    <div class="content-area">
      {#if appState.currentView() === 'company' && appState.selectedCompany}
        <CompanyDetail
          company={appState.selectedCompany}
          on:aggregateSelected={handleAggregateSelectedFromCompanyDetail}
          on:filingSelected={handleFilingSelected}
        />
      {:else if appState.currentView() === 'filing' && appState.selectedFiling}
        <FilingDetail
          filing={appState.selectedFiling}
          company={appState.selectedCompany ?? undefined}
          on:documentSelected={handleDocumentSelected}
        />
      {:else if appState.currentView() === 'aggregate' && appState.selectedAggregate}
        <AggregateDetail
          aggregate={appState.selectedAggregate}
          on:completionSelected={handleCompletionSelected}
        />
      {:else if appState.currentView() === 'completion' && appState.selectedCompletion}
        <CompletionDetail
          completion={appState.selectedCompletion}
          on:documentSelected={handleDocumentSelected}
        />
      {:else if appState.currentView() === 'document' && appState.selectedDocument}
        <DocumentViewer
          document={appState.selectedDocument}
          completion={appState.selectedCompletion ?? undefined}
        />
      {:else}
        <PlaceholderCard completion={undefined} />
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
