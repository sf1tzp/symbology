<script lang="ts">
  import { getLogger } from '$utils/logger';
  import CompanySelector from '$components/company/CompanySelector.svelte';
  import DocumentViewer from '$components/documents/DocumentViewer.svelte';
  import PlaceholderCard from '$components/ui/PlaceholderCard.svelte';
  import Header from '$components/ui/Header.svelte';
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
      actions.initializeDisclaimer();
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
  <div class="dashboard">
    <!-- Sidebar column -->
    <div class="selectors full-height">
      <Header />
      <div class="company-selector-wrapper">
        <CompanySelector
          on:companySelected={handleCompanySelected}
          on:companyCleared={handleCompanyCleared}
        />
      </div>
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
          company={appState.selectedCompany ?? undefined}
          on:completionSelected={handleCompletionSelected}
        />
      {:else if appState.currentView() === 'completion' && appState.selectedCompletion}
        <CompletionDetail
          completion={appState.selectedCompletion}
          company={appState.selectedCompany ?? undefined}
          filing={appState.selectedFiling ?? undefined}
          on:documentSelected={handleDocumentSelected}
        />
      {:else if appState.currentView() === 'document' && appState.selectedDocument}
        <DocumentViewer
          document={appState.selectedDocument}
          completion={appState.selectedCompletion ?? undefined}
        />
      {:else}
        <PlaceholderCard />
      {/if}
    </div>
  </div>
</main>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    height: 100%;
    min-height: 0;
    box-sizing: border-box;
  }

  .selectors {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    z-index: 100;
    height: 100%;
    min-height: 0;
    flex: 1 1 0;
    box-sizing: border-box;
  }

  .company-selector-wrapper {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
  }

  .content-area {
    height: 100%;
    min-height: 0;
    overflow-y: auto;
    flex: 1 1 0;
    box-sizing: border-box;
  }

  @media (min-width: 768px) {
    .dashboard {
      flex-direction: row;
    }

    .dashboard .selectors {
      width: 30%;
      max-width: 350px;
      height: 100vh;
      min-height: 0;
      flex: 1 1 0;
      box-sizing: border-box;
    }

    .dashboard .content-area {
      width: 70%;
      flex-grow: 1;
      min-height: 0;
      box-sizing: border-box;
    }
  }
</style>
