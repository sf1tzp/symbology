<script lang="ts">
  import { getComponentLogger } from '$utils/logger';
  import { config, setRuntimeConfig } from '$utils/config';
  import { loadConfig } from '$utils/config-service';
  import { Spinner } from 'kampsy-ui';
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
    <div class="flex flex-col items-center justify-center h-screen gap-4 p-6 text-center">
      <Spinner size="large" />
      <p>Loading application configuration...</p>
      {#if initializationError}
        <div class="bg-red-50 border border-red-300 text-red-600 p-4 rounded-md max-w-md">
          <p>⚠️ {initializationError}</p>
          <p>Continuing with fallback configuration...</p>
        </div>
      {/if}
    </div>
  {:else}
    <!-- Main application - only render after config is loaded -->
    <div class="flex flex-col md:flex-row gap-1 md:gap-4 h-full md:h-screen min-h-0 box-border">
      <!-- Sidebar column -->
      <div
        class="flex flex-col gap-2 z-[100] h-full min-h-0 flex-none md:flex-1 box-border md:w-[30%] md:max-w-[350px] max-h-[35vh] md:max-h-none md:h-screen"
      >
        <Header />
        <div class="flex-1 min-h-0 flex flex-col box-border">
          <CompanySelector
            on:companySelected={handleCompanySelected}
            on:companyCleared={handleCompanyCleared}
          />
        </div>
      </div>

      <!-- Content area with conditional layout based on currentView derived state -->
      <div
        class="h-full min-h-[65vh] md:min-h-0 overflow-y-auto flex-1 box-border md:w-[70%] md:flex-grow px-1 md:px-0"
      >
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
  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--color-border);
    border-top: 4px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
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
  }
</style>
