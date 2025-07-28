<script lang="ts">
  import { getComponentLogger } from '$utils/logger';
  import { config, setRuntimeConfig } from '$utils/config';
  import { loadConfig } from '$utils/config-service';
  import CompanySelector from '$components/company/CompanySelector.svelte';
  import DocumentDetail from '$components/documents/DocumentDetail.svelte';
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

  // State for initialization
  let configLoaded = $state(false);
  let initializationError = $state<string | null>(null);

  // Logger will be created after config is loaded
  let logger: ReturnType<typeof getComponentLogger>;

  // Initialize configuration first, then everything else
  $effect(() => {
    if (!configLoaded) {
      loadConfig()
        .then((runtimeConfig) => {
          setRuntimeConfig(runtimeConfig);

          // Now create logger with correct config
          logger = getComponentLogger('SymbologyApp');

          // Log environment variables from the loaded config
          logger.info('runtime_configuration_loaded', {
            environment: runtimeConfig.environment,
            logLevel: runtimeConfig.logging.level,
            enableBackendLogging: runtimeConfig.logging.enableBackendLogging,
            apiBaseUrl: runtimeConfig.api.baseUrl,
            enableDebugMode: runtimeConfig.features.enableDebugMode,
          });

          actions.initializeTheme();
          actions.initializeDisclaimer();
          configLoaded = true;
        })
        .catch((error) => {
          // Create logger with fallback config early for error reporting
          const fallbackLogger = getComponentLogger('App');
          fallbackLogger.error('config_load_failed', { error });

          initializationError = `Failed to load configuration: ${error.message}`;

          // Create logger with fallback config
          logger = getComponentLogger('App');

          logger.warn('config_api_failed', { error });

          logger.info('app_initializing_fallback', {
            environment: config.env,
            userAgent: navigator.userAgent,
            configSource: 'fallback',
          });

          actions.initializeTheme();
          actions.initializeDisclaimer();
          configLoaded = true;
        });
    }
  });

  // Event handlers - now much simpler since state is managed centrally
  function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
    logger.info('company_selected', {
      companyId: event.detail.id,
      companyName: event.detail.name,
      tickers: event.detail.tickers,
    });
    actions.selectCompany(event.detail);
  }

  function handleCompanyCleared() {
    logger.info('company_selection_cleared');
    actions.clearAll();
  }

  function handleCompletionSelected(event: CustomEvent<CompletionResponse>) {
    logger.info('completion_selected', {
      completion_id: event.detail.id,
      model: event.detail.model,
    });
    actions.selectCompletion(event.detail);
  }

  function handleAggregateSelectedFromCompanyDetail(event: CustomEvent<AggregateResponse>) {
    logger.info('aggregate_selected', {
      aggregateId: event.detail.id,
      companyId: event.detail.company_id,
      documentType: event.detail.document_type,
    });
    actions.selectAggregate(event.detail);
  }

  function handleFilingSelected(event: CustomEvent<FilingResponse>) {
    logger.info('filing_selected', {
      filingId: event.detail.id,
      companyId: event.detail.company_id,
      filingType: event.detail.filing_type,
      filingDate: event.detail.filing_date,
    });
    actions.selectFiling(event.detail);
  }

  function handleDocumentSelected(event: CustomEvent<DocumentResponse>) {
    logger.info('document_selected', {
      documentId: event.detail.id,
      filingId: event.detail.filing_id,
      documentName: event.detail.document_name,
    });
    actions.selectDocument(event.detail);
  }
</script>

<main>
  {#if !configLoaded}
    <!-- Loading state while config is being fetched -->
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading application configuration...</p>
      {#if initializationError}
        <div class="error-message">
          <p>⚠️ {initializationError}</p>
          <p>Continuing with fallback configuration...</p>
        </div>
      {/if}
    </div>
  {:else}
    <!-- Main application - only render after config is loaded -->
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
          <DocumentDetail
            document={appState.selectedDocument}
            completion={appState.selectedCompletion ?? undefined}
          />
        {:else}
          <PlaceholderCard />
        {/if}
      </div>
    </div>
  {/if}
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

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    gap: var(--space-md);
    padding: var(--space-lg);
    text-align: center;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--color-border);
    border-top: 4px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .error-message {
    background: var(--color-error-bg, #fee);
    border: 1px solid var(--color-error, #f44);
    color: var(--color-error, #f44);
    padding: var(--space-md);
    border-radius: var(--radius-md);
    max-width: 400px;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
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
