<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
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

  // Fetch aggregates when company changes
  $effect(() => {
    if (company) {
      fetchAggregates();
      fetchFilings();
    }
  });

  async function fetchAggregates() {
    loading = true;
    error = null;
    try {
      logger.debug('[CompanyDetail] Fetching aggregates for company', { companyId: company.id });

      // Use the first ticker to fetch aggregates since the API is ticker-based
      if (!company.tickers?.length) {
        logger.warn('[CompanyDetail] No tickers available for company', {
          companyId: company.id,
        });
        availableAggregates = [];
        return;
      }

      const ticker = company.tickers[0];
      const aggregates = await fetchApi<AggregateResponse[]>(`/api/aggregates/by-ticker/${ticker}`);
      availableAggregates = aggregates;
      logger.debug('[CompanyDetail] Fetched aggregates', { count: aggregates.length, ticker });
    } catch (err) {
      logger.error('[CompanyDetail] Failed to fetch aggregates', { error: err });
      error = err instanceof Error ? err.message : 'Failed to load aggregates';
      availableAggregates = [];
    } finally {
      loading = false;
    }
  }

  async function fetchFilings() {
    filingsLoading = true;
    filingsError = null;
    try {
      logger.debug('[CompanyDetail] Fetching filings for company', { companyId: company.id });

      const filings = await fetchApi<FilingResponse[]>(`/api/filings/by-company/${company.id}`);
      availableFilings = filings.sort(
        (a, b) => new Date(b.filing_date).getTime() - new Date(a.filing_date).getTime()
      );
      logger.debug('[CompanyDetail] Fetched filings', { count: filings.length });
    } catch (err) {
      logger.error('[CompanyDetail] Failed to fetch filings', { error: err });
      filingsError = err instanceof Error ? err.message : 'Failed to load filings';
      availableFilings = [];
    } finally {
      filingsLoading = false;
    }
  }

  function handleAggregateClick(aggregate: AggregateResponse) {
    logger.debug('[CompanyDetail] Aggregate selected', {
      aggregateId: aggregate.id,
      documentType: aggregate.document_type,
    });
    dispatch('aggregateSelected', aggregate);
  }

  function handleFilingClick(filing: FilingResponse) {
    logger.debug('[CompanyDetail] Filing selected', {
      filingId: filing.id,
      accessionNumber: filing.accession_number,
    });
    dispatch('filingSelected', filing);
  }

  function toggleFilingsCollapsed() {
    filingsCollapsed = !filingsCollapsed;
  }
</script>

<div class="company-detail card">
  <header class="company-header">
    <div class="header-top">
      <BackButton label="Back" on:back={actions.navigateBackFromCompany} />
      <h1>{formatTitleCase(company.display_name || company.name)}</h1>
      <div class="company-meta">
        {#if company.tickers?.length}
          <div class="tickers">
            <span class="ticker">{company.tickers[0]}</span>
          </div>
        {/if}
        {#if company.exchanges?.length}
          <div class="exchanges">
            {company.exchanges[0]}
          </div>
        {/if}
      </div>
    </div>
  </header>

  <section class="company-summary">
    {#if cleanContent(company.summary)}
      <div class="summary-text">
        <MarkdownContent content={cleanContent(company.summary) || ''} />
      </div>
    {/if}

    <!-- <MetaItems items={summaryItems} /> -->
  </section>

  <section class="aggregates-section">
    <h2>This summary was generated from the following reports:</h2>
    {#if loading}
      <LoadingState message="Loading analysis..." />
    {:else if error}
      <ErrorState message="Error loading analysis: {error}" onRetry={fetchAggregates} />
    {:else if availableAggregates.length > 0}
      <div class="aggregates-list">
        {#each availableAggregates as aggregate (aggregate.id)}
          <button
            class="aggregate-link"
            onclick={() => handleAggregateClick(aggregate)}
            onkeydown={(e) => e.key === 'Enter' && handleAggregateClick(aggregate)}
          >
            {formatDocumentType(aggregate.document_type)}
          </button>
        {/each}
      </div>
    {:else}
      <div class="no-aggregates">
        <p>No analysis available for this company yet.</p>
      </div>
    {/if}
  </section>

  <section class="filings-section">
    <div class="section-header">
      <h2>SEC Filings</h2>
      <button
        class="toggle-button"
        onclick={toggleFilingsCollapsed}
        aria-label={filingsCollapsed ? 'Show filings' : 'Hide filings'}
      >
        <span class="toggle-icon" class:collapsed={filingsCollapsed}>▼</span>
      </button>
    </div>

    {#if !filingsCollapsed}
      {#if filingsLoading}
        <LoadingState message="Loading filings..." />
      {:else if filingsError}
        <ErrorState message="Error loading filings: {filingsError}" onRetry={fetchFilings} />
      {:else if availableFilings.length > 0}
        <p>We have processed information from these filings:</p>
        <div class="filings-container">
          <div class="filings-list">
            {#each availableFilings as filing (filing.id)}
              <button
                class="filing-item"
                onclick={() => handleFilingClick(filing)}
                onkeydown={(e) => e.key === 'Enter' && handleFilingClick(filing)}
              >
                <div class="filing-header">
                  <div class="filing-type-info">
                    <h3 class="filing-type">
                      {formatYear(filing.period_of_report)}
                      {filing.filing_type}
                    </h3>
                    <span class="filing-description">{getFilingTypeLabel(filing.filing_type)}</span>
                  </div>
                </div>
              </button>
            {/each}
          </div>
        </div>
      {:else}
        <div class="no-filings">
          <p>No SEC filings available for this company.</p>
        </div>
      {/if}
    {/if}
  </section>

  <section class="financials-section">
    <h2>Financials</h2>
    <p class="unimplemented">Quantitative analyis coming soon</p>
  </section>
</div>

<style>
  .company-detail {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

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

  .company-meta {
    display: flex;
    gap: var(--space-md);
    align-items: center;
    margin-top: var(--space-sm);
  }

  .tickers {
    display: flex;
    gap: var(--space-xs);
  }

  .ticker {
    background-color: var(--color-primary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.9rem;
  }

  .exchanges {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .aggregates-section h2,
  .filings-section h2,
  .financials-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-md);
  }

  .section-header h2 {
    margin: 0;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
    flex: 1;
  }

  .toggle-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    transition: background-color 0.2s ease;
    margin-left: var(--space-sm);
  }

  .toggle-button:hover {
    background-color: var(--color-background);
  }

  .toggle-button:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .toggle-icon {
    display: inline-block;
    font-size: 0.8rem;
    color: var(--color-text-light);
    transition: transform 0.2s ease;
  }

  .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

  .summary-text {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
  }

  .aggregates-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-md);
    align-items: center;
  }

  .aggregate-link {
    background: none;
    border: none;
    color: var(--color-primary);
    text-decoration: underline;
    cursor: pointer;
    font-size: 1rem;
    font-family: inherit;
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    transition: background-color 0.2s ease;
  }

  .aggregate-link:hover {
    background-color: var(--color-background);
    text-decoration: none;
  }

  .aggregate-link:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .no-aggregates,
  .no-filings {
    color: var(--color-text-light);
    font-style: italic;
    margin: 0;
    padding: var(--space-md);
    text-align: center;
  }

  .filings-container {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
  }

  .filings-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    max-height: 400px;
    overflow-y: auto;
  }

  .filing-item {
    display: block;
    width: 100%;
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition: transform 0.2s ease;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: inherit;
    color: inherit;
  }

  .filing-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
  }

  .filing-header {
    margin-bottom: var(--space-sm);
  }

  .filing-type-info {
    display: flex;
    flex-direction: column;
  }

  .filing-type {
    margin: 0;
    color: var(--color-primary);
    font-size: 1rem;
    font-weight: var(--font-weight-bold);
  }

  .filing-description {
    margin: 0;
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .unimplemented {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
  }

  @media (max-width: 768px) {
    .company-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
