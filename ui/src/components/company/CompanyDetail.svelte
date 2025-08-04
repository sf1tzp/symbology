<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import { config } from '$utils/config';
  import type {
    CompanyResponse,
    AggregateResponse,
    FilingResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import {
    formatYear,
    cleanContent,
    getFilingTypeLabel,
    formatDocumentType,
    formatTitleCase,
  } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import BackButton from '$components/ui/BackButton.svelte';
  import { actions } from '$utils/state-manager.svelte';
  import { Button, Tabs } from 'kampsy-ui';

  const logger = getLogger('CompanyDetail');
  const dispatch = createEventDispatcher<{
    aggregateSelected: AggregateResponse;
    filingSelected: FilingResponse;
  }>();

  const { company } = $props<{
    company: CompanyResponse;
  }>();

  let availableAggregates = $state<AggregateResponse[]>([]);
  let availableFilings = $state<FilingResponse[]>([]);
  let loading = $state(false);
  let filingsLoading = $state(false);
  let error = $state<string | null>(null);
  let filingsError = $state<string | null>(null);
  let filingsCollapsed = $state(true);
  let selectedAggregateId = $state<string>('');

  // Fetch aggregates when company changes
  $effect(() => {
    if (company) {
      fetchAggregates();
      fetchFilings();
    }
  });

  // Handle tab selection
  $effect(() => {
    if (selectedAggregateId && availableAggregates.length > 0) {
      const aggregate = availableAggregates.find((a) => a.id === selectedAggregateId);
      if (aggregate) {
        handleAggregateClick(aggregate);
      }
    }
  });

  async function fetchAggregates() {
    loading = true;
    error = null;
    try {
      logger.info('aggregates_fetch_start', { companyId: company.id });

      // Use the first ticker to fetch aggregates since the API is ticker-based
      if (!company.tickers?.length) {
        logger.warn('aggregates_fetch_no_tickers', { companyId: company.id });
        availableAggregates = [];
        return;
      }

      const ticker = company.tickers[0];
      const apiUrl = `${config.api.baseUrl}/aggregates/by-ticker/${ticker}`;

      const aggregates = await fetchApi<AggregateResponse[]>(apiUrl);
      availableAggregates = aggregates;
      // // Set the first aggregate as selected by default
      // if (aggregates.length > 0 && !selectedAggregateId) {
      //   selectedAggregateId = aggregates[0].id;
      // }
      logger.info('aggregates_fetch_success', { count: aggregates.length, ticker });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('aggregates_fetch_failed', {
        error: errorMessage,
        companyId: company.id,
        ticker: company.tickers?.[0],
      });
      error = errorMessage;
      availableAggregates = [];
    } finally {
      loading = false;
    }
  }

  async function fetchFilings() {
    filingsLoading = true;
    filingsError = null;
    try {
      logger.info('filings_fetch_start', { companyId: company.id });

      const filings = await fetchApi<FilingResponse[]>(
        `${config.api.baseUrl}/filings/by-company/${company.id}`
      );
      availableFilings = filings.sort(
        (a, b) => new Date(b.filing_date).getTime() - new Date(a.filing_date).getTime()
      );
      logger.info('filings_fetch_success', { count: filings.length });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('filings_fetch_failed', {
        error: errorMessage,
        companyId: company.id,
      });
      filingsError = errorMessage;
      availableFilings = [];
    } finally {
      filingsLoading = false;
    }
  }

  function handleAggregateClick(aggregate: AggregateResponse) {
    logger.info('aggregate_selected', { aggregateId: aggregate.id });
    dispatch('aggregateSelected', aggregate);
  }

  function handleFilingClick(filing: FilingResponse) {
    logger.info('filing_selected', { filingId: filing.id });
    dispatch('filingSelected', filing);
  }

  function toggleFilingsCollapsed() {
    filingsCollapsed = !filingsCollapsed;
  }
</script>

<div class="card content-container">
  <header class="company-header">
    <div class="header-top">
      <BackButton label="Back" on:back={actions.navigateBackFromCompany} />
      <h1>{formatTitleCase(company.display_name || company.name)}</h1>
      <div class="meta-container">
        {#if company.tickers?.length}
          <span class="badge">{company.tickers[0]}</span>
        {/if}
        <!-- {#if company.exchanges?.length}
          <span class="meta-item">{company.exchanges[0]}</span>
        {/if} -->
      </div>
    </div>
  </header>

  <section class="section-container">
    {#if cleanContent(company.summary)}
      <div class="content-box">
        <MarkdownContent content={cleanContent(company.summary) || ''} />
      </div>
    {/if}
  </section>

  <section class="section-container">
    <h2 class="section-title-small">Click to expand:</h2>
    {#if loading}
      <LoadingState message="Loading analysis..." />
    {:else if error}
      <ErrorState message="Error loading analysis: {error}" onRetry={fetchAggregates} />
    {:else if availableAggregates.length > 0}
      <div class="w-full flex flex-wrap gap-4 justify-between">
        {#each availableAggregates as aggregate (aggregate.id)}
          <Button
            onclick={() => handleAggregateClick(aggregate)}
            onkeydown={(e) => e.key === 'Enter' && handleAggregateClick(aggregate)}
          >
            {formatDocumentType(aggregate.document_type)}
          </Button>
        {/each}
      </div>
    {:else}
      <div class="no-content">
        <p>No analysis available for this company yet.</p>
      </div>
    {/if}
  </section>

  <section class="section-container">
    <div
      class="section-header"
      role="button"
      tabindex="0"
      onclick={toggleFilingsCollapsed}
      onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && toggleFilingsCollapsed()}
      aria-label={filingsCollapsed ? 'Show filings' : 'Hide filings'}
    >
      <h2 class="section-title">SEC Filings. Click for details...</h2>
      <span class="icon" class:icon-collapsed={filingsCollapsed}>▼</span>
    </div>

    <div class:collapsed={filingsCollapsed}>
      {#if filingsLoading}
        <LoadingState message="Loading filings..." />
      {:else if filingsError}
        <ErrorState message="Error loading filings: {filingsError}" onRetry={fetchFilings} />
      {:else if availableFilings.length > 0}
        <p>We've gathered information from these filings:</p>
        <div class="list-container">
          {#each availableFilings as filing (filing.id)}
            <Button
              size="medium"
              onclick={() => handleFilingClick(filing)}
              onkeydown={(e) => e.key === 'Enter' && handleFilingClick(filing)}
              class="w-full text-left"
            >
              <div class="filing-header">
                <div class="filing-type-info">
                  <h3 class="filing-type">
                    {formatYear(filing.period_of_report)}
                    {filing.filing_type}
                  </h3>
                  <span class="meta-item">{getFilingTypeLabel(filing.filing_type)}</span>
                </div>
              </div>
            </Button>
          {/each}
        </div>
      {:else}
        <div class="no-content">
          <p>No SEC filings available for this company.</p>
        </div>
      {/if}
    </div>
  </section>

  <!-- <section class="section-container"> -->
  <!--   <h2 class="section-title">Financials</h2> -->
  <!--   <MarkdownContent content={'Financials Coming Soon!'} /> -->
  <!-- </section> -->
</div>

<style>
  .header-top {
    display: flex;
    align-items: flex-start;
    gap: var(--space-md);
    margin-bottom: var(--space-sm);
  }

  .company-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
    flex: 1;
  }

  .filing-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }

  .filing-type-info {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    text-align: left;
  }

  .filing-type {
    margin: 0;
    font-size: 1rem;
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
  }
</style>
