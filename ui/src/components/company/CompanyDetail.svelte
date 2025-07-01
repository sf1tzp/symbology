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
    formatDate,
    formatModelName,
    cleanContent,
    getFilingTypeLabel,
    formatDocumentType,
  } from '$utils/formatters';
  import LoadingState from '$components/ui/LoadingState.svelte';
  import ErrorState from '$components/ui/ErrorState.svelte';
  import MarkdownContent from '$components/ui/MarkdownContent.svelte';
  import MetaItems from '$components/ui/MetaItems.svelte';

  const logger = getLogger('CompanyDetail');
  const dispatch = createEventDispatcher<{
    aggregateSelected: AggregateResponse;
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
    logger.debug('[CompanyDetail] Filing clicked', {
      filingId: filing.id,
      accessionNumber: filing.accession_number,
    });
    if (filing.filing_url) {
      window.open(filing.filing_url, '_blank');
    }
  }

  // Prepare company summary meta items
  const summaryItems = $derived([
    ...(company.sic_description ? [{ label: 'Industry', value: company.sic_description }] : []),
    ...(company.entity_type ? [{ label: 'Entity Type', value: company.entity_type }] : []),
    ...(company.fiscal_year_end
      ? [{ label: 'Fiscal Year End', value: formatDate(company.fiscal_year_end) }]
      : []),
    ...(company.cik ? [{ label: 'CIK', value: company.cik, mono: true }] : []),
  ]);

  // Prepare aggregate meta items for each aggregate
  function getAggregateMetaItems(aggregate: AggregateResponse) {
    return [
      { label: 'Created', value: formatDate(aggregate.created_at) },
      ...(aggregate.temperature ? [{ label: 'Temperature', value: aggregate.temperature }] : []),
      ...(aggregate.total_duration
        ? [{ label: 'Duration', value: `${aggregate.total_duration.toFixed(1)}s` }]
        : []),
    ];
  }

  // Prepare filing meta items for each filing
  function getFilingMetaItems(filing: FilingResponse) {
    return [
      { label: 'Filed', value: formatDate(filing.filing_date) },
      ...(filing.period_of_report
        ? [{ label: 'Period', value: formatDate(filing.period_of_report) }]
        : []),
      { label: 'Accession', value: filing.accession_number, mono: true },
    ];
  }
</script>

<div class="company-detail card">
  <header class="company-header">
    <h1>{company.display_name || company.name}</h1>
    <div class="company-meta">
      {#if company.tickers?.length}
        <div class="tickers">
          {#each company.tickers as ticker (ticker)}
            <span class="ticker">{ticker}</span>
          {/each}
        </div>
      {/if}
      {#if company.exchanges?.length}
        <div class="exchanges">
          {company.exchanges.join(', ')}
        </div>
      {/if}
    </div>
  </header>

  <section class="company-summary">
    <h2>Company Summary</h2>

    {#if cleanContent(company.summary)}
      <div class="summary-text">
        <MarkdownContent content={cleanContent(company.summary) || ''} />
      </div>
    {/if}

    <MetaItems items={summaryItems} />
  </section>

  <section class="aggregates-section">
    <h2>Available Analysis</h2>

    {#if loading}
      <LoadingState message="Loading analysis..." />
    {:else if error}
      <ErrorState message="Error loading analysis: {error}" onRetry={fetchAggregates} />
    {:else if availableAggregates.length > 0}
      <div class="aggregates-list">
        {#each availableAggregates as aggregate (aggregate.id)}
          <div
            class="aggregate-item"
            role="button"
            tabindex="0"
            onclick={() => handleAggregateClick(aggregate)}
            onkeydown={(e) => e.key === 'Enter' && handleAggregateClick(aggregate)}
          >
            <div class="aggregate-header">
              <h3 class="aggregate-title">{formatDocumentType(aggregate.document_type)}</h3>
              <span class="aggregate-model">{formatModelName(aggregate.model)}</span>
            </div>

            <MetaItems items={getAggregateMetaItems(aggregate)} columns={3} variant="surface" />

            {#if cleanContent(aggregate.summary)}
              <div class="aggregate-preview">
                <MarkdownContent
                  content={(() => {
                    const cleaned = cleanContent(aggregate.summary) || '';
                    return cleaned.length > 150 ? cleaned.substring(0, 150) + '...' : cleaned;
                  })()}
                />
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="no-aggregates">
        <p>No analysis available for this company yet.</p>
      </div>
    {/if}
  </section>

  <section class="filings-section">
    <h2>SEC Filings</h2>

    {#if filingsLoading}
      <LoadingState message="Loading filings..." />
    {:else if filingsError}
      <ErrorState message="Error loading filings: {filingsError}" onRetry={fetchFilings} />
    {:else if availableFilings.length > 0}
      <div class="filings-container">
        <div class="filings-list">
          {#each availableFilings as filing (filing.id)}
            <button
              class="filing-item"
              class:clickable={filing.filing_url}
              disabled={!filing.filing_url}
              onclick={() => handleFilingClick(filing)}
              onkeydown={(e) => e.key === 'Enter' && handleFilingClick(filing)}
            >
              <div class="filing-header">
                <div class="filing-type-info">
                  <h3 class="filing-type">{filing.filing_type}</h3>
                  <span class="filing-description">{getFilingTypeLabel(filing.filing_type)}</span>
                </div>
              </div>

              <MetaItems items={getFilingMetaItems(filing)} columns={3} variant="surface" />

              {#if filing.filing_url}
                <div class="filing-link">
                  <span class="link-indicator">Click to view on SEC website</span>
                </div>
              {/if}
            </button>
          {/each}
        </div>
      </div>
    {:else}
      <div class="no-filings">
        <p>No SEC filings available for this company.</p>
      </div>
    {/if}
  </section>

  <section class="financials-section">
    <h2>Financials</h2>
    <p class="unimplemented">Financial data display is not yet implemented</p>
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

  .company-header h1 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.5rem;
    font-weight: var(--font-weight-bold);
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

  .company-summary h2,
  .aggregates-section h2,
  .filings-section h2,
  .financials-section h2 {
    margin: 0 0 var(--space-md) 0;
    color: var(--color-text);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
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
    flex-direction: column;
    gap: var(--space-md);
  }

  .aggregate-item {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .aggregate-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
  }

  .aggregate-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-sm);
  }

  .aggregate-title {
    margin: 0;
    color: var(--color-primary);
    font-size: 1.1rem;
    font-weight: var(--font-weight-bold);
  }

  .aggregate-model {
    background-color: var(--color-primary);
    color: var(--color-surface);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--border-radius);
    font-weight: var(--font-weight-bold);
    font-size: 0.8rem;
  }

  .aggregate-preview {
    margin-top: var(--space-md);
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
    color: var(--color-text);
    line-height: 1.5;
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

  .filing-item:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .filing-item:not(:disabled):hover {
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

  .filing-link {
    margin-top: var(--space-sm);
    text-align: center;
  }

  .link-indicator {
    font-size: 0.8rem;
    color: var(--color-text-light);
    font-style: italic;
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
