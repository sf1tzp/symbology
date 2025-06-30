<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi } from '$utils/generated-api-types';
  import type {
    CompanyResponse,
    AggregateResponse,
    FilingResponse,
  } from '$utils/generated-api-types';
  import { createEventDispatcher } from 'svelte';
  import { marked } from 'marked';

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

  function formatDate(dateString: string | undefined) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  }

  function cleanSummaryText(summary: string | undefined): string | undefined {
    if (!summary) return undefined;

    // Remove <think>...</think> blocks and any content before them
    let cleaned = summary.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

    // Also handle cases where there might be thinking content without tags
    // Look for patterns that suggest internal reasoning at the start
    cleaned = cleaned.replace(
      /^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
      ''
    );

    // Trim any remaining whitespace
    cleaned = cleaned.trim();

    return cleaned || undefined;
  }

  function renderMarkdown(text: string): string {
    const result = marked.parse(text, {
      breaks: true,
      gfm: true,
      async: false,
    });
    return typeof result === 'string' ? result : '';
  }

  function getFilingTypeLabel(filingType: string): string {
    const typeLabels: Record<string, string> = {
      '10-K': 'Annual Report',
      '10-Q': 'Quarterly Report',
      '8-K': 'Current Report',
      '10-K/A': 'Annual Report (Amendment)',
      '10-Q/A': 'Quarterly Report (Amendment)',
      'DEF 14A': 'Proxy Statement',
      'S-1': 'Registration Statement',
      'S-3': 'Registration Statement',
      'S-4': 'Registration Statement',
      'S-8': 'Registration Statement',
    };
    return typeLabels[filingType] || filingType;
  }
</script>

<div class="company-detail card">
  <header class="company-header">
    <h1>{company.display_name || company.name}</h1>
    <div class="company-meta">
      {#if company.tickers?.length}
        <div class="tickers">
          {#each company.tickers as ticker}
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

    {#if cleanSummaryText(company.summary)}
      <div class="summary-text">
        {@html renderMarkdown(cleanSummaryText(company.summary) || '')}
      </div>
    {/if}

    <div class="summary-grid">
      {#if company.sic_description}
        <div class="summary-item">
          <span class="label">Industry:</span>
          <span>{company.sic_description}</span>
        </div>
      {/if}
      {#if company.entity_type}
        <div class="summary-item">
          <span class="label">Entity Type:</span>
          <span>{company.entity_type}</span>
        </div>
      {/if}
      {#if company.fiscal_year_end}
        <div class="summary-item">
          <span class="label">Fiscal Year End:</span>
          <span>{formatDate(company.fiscal_year_end)}</span>
        </div>
      {/if}
      {#if company.cik}
        <div class="summary-item">
          <span class="label">CIK:</span>
          <span class="mono">{company.cik}</span>
        </div>
      {/if}
    </div>
  </section>

  <section class="aggregates-section">
    <h2>Available Analysis</h2>

    {#if loading}
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <p>Loading analysis...</p>
      </div>
    {:else if error}
      <div class="error-message">
        <p>Error loading analysis: {error}</p>
        <button onclick={fetchAggregates} class="retry-button">Retry</button>
      </div>
    {:else if availableAggregates.length > 0}
      <div class="aggregates-list">
        {#each availableAggregates as aggregate}
          <div
            class="aggregate-item"
            role="button"
            tabindex="0"
            onclick={() => handleAggregateClick(aggregate)}
            onkeydown={(e) => e.key === 'Enter' && handleAggregateClick(aggregate)}
          >
            <div class="aggregate-header">
              <h3 class="aggregate-title">
                {#if aggregate.document_type === 'MDA'}
                  Management Discussion & Analysis
                {:else if aggregate.document_type === 'DESCRIPTION'}
                  Business Description
                {:else if aggregate.document_type === 'RISK_FACTORS'}
                  Risk Factors
                {:else}
                  {aggregate.document_type || 'Unknown Analysis'}
                {/if}
              </h3>
              <span class="aggregate-model">{aggregate.model.replace('_', ' ').toUpperCase()}</span>
            </div>

            <div class="aggregate-meta">
              <div class="meta-item">
                <span class="label">Created:</span>
                <span>{formatDate(aggregate.created_at)}</span>
              </div>
              {#if aggregate.temperature}
                <div class="meta-item">
                  <span class="label">Temperature:</span>
                  <span>{aggregate.temperature}</span>
                </div>
              {/if}
              {#if aggregate.total_duration}
                <div class="meta-item">
                  <span class="label">Duration:</span>
                  <span>{aggregate.total_duration.toFixed(1)}s</span>
                </div>
              {/if}
            </div>

            {#if cleanSummaryText(aggregate.summary)}
              <div class="aggregate-preview">
                {@html (() => {
                  const cleaned = cleanSummaryText(aggregate.summary) || '';
                  const truncated =
                    cleaned.length > 150 ? cleaned.substring(0, 150) + '...' : cleaned;
                  return renderMarkdown(truncated);
                })()}
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
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <p>Loading filings...</p>
      </div>
    {:else if filingsError}
      <div class="error-message">
        <p>Error loading filings: {filingsError}</p>
        <button onclick={fetchFilings} class="retry-button">Retry</button>
      </div>
    {:else if availableFilings.length > 0}
      <div class="filings-container">
        <div class="filings-list">
          {#each availableFilings as filing}
            <div
              class="filing-item"
              class:clickable={filing.filing_url}
              role={filing.filing_url ? 'button' : 'listitem'}
              tabindex={filing.filing_url ? 0 : undefined}
              onclick={() => handleFilingClick(filing)}
              onkeydown={(e) => e.key === 'Enter' && handleFilingClick(filing)}
            >
              <div class="filing-header">
                <div class="filing-type-info">
                  <h3 class="filing-type">{filing.filing_type}</h3>
                  <span class="filing-description">{getFilingTypeLabel(filing.filing_type)}</span>
                </div>
                <div class="filing-dates">
                  <div class="filing-date">
                    <span class="label">Filed:</span>
                    <span>{formatDate(filing.filing_date)}</span>
                  </div>
                  {#if filing.period_of_report}
                    <div class="period-date">
                      <span class="label">Period:</span>
                      <span>{formatDate(filing.period_of_report)}</span>
                    </div>
                  {/if}
                </div>
              </div>

              <div class="filing-meta">
                <div class="accession-number">
                  <span class="label">Accession:</span>
                  <span class="mono">{filing.accession_number}</span>
                </div>
                {#if filing.filing_url}
                  <div class="filing-link">
                    <span class="link-indicator">Click to view on SEC website</span>
                  </div>
                {/if}
              </div>
            </div>
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

  .summary-text :global(p) {
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.6;
    color: var(--color-text);
  }

  .summary-text :global(p:last-child) {
    margin-bottom: 0;
  }

  .summary-text :global(h1),
  .summary-text :global(h2),
  .summary-text :global(h3),
  .summary-text :global(h4),
  .summary-text :global(h5),
  .summary-text :global(h6) {
    margin: var(--space-md) 0 var(--space-sm) 0;
    color: var(--color-primary);
  }

  .summary-text :global(h1:first-child),
  .summary-text :global(h2:first-child),
  .summary-text :global(h3:first-child),
  .summary-text :global(h4:first-child),
  .summary-text :global(h5:first-child),
  .summary-text :global(h6:first-child) {
    margin-top: 0;
  }

  .summary-text :global(ul),
  .summary-text :global(ol) {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .summary-text :global(li) {
    margin: var(--space-xs) 0;
    line-height: 1.5;
  }

  .summary-text :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .summary-text :global(em) {
    font-style: italic;
  }

  .summary-text :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.9em;
  }

  .summary-text :global(pre) {
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: var(--space-sm) 0;
  }

  .summary-text :global(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--space-md);
    margin: var(--space-sm) 0;
    font-style: italic;
    color: var(--color-text-light);
  }

  .summary-grid {
    display: grid;
    gap: var(--space-sm);
  }

  .summary-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .summary-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
  }

  .summary-item span:not(.label) {
    color: var(--color-text-light);
  }

  .meta-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .meta-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    font-size: 0.9rem;
  }

  .meta-item span:not(.label) {
    color: var(--color-text-light);
    font-family: monospace;
    font-size: 0.8rem;
  }

  .mono {
    font-family: monospace;
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

  .aggregate-meta {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  .meta-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-surface);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .aggregate-preview {
    color: var(--color-text);
    line-height: 1.5;
  }

  .aggregate-preview :global(p) {
    margin: 0 0 var(--space-xs) 0;
    line-height: 1.5;
    color: var(--color-text);
  }

  .aggregate-preview :global(p:last-child) {
    margin-bottom: 0;
  }

  .aggregate-preview :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .aggregate-preview :global(em) {
    font-style: italic;
  }

  .aggregate-preview :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.85em;
  }

  .aggregate-preview :global(ul),
  .aggregate-preview :global(ol) {
    margin: var(--space-xs) 0;
    padding-left: var(--space-md);
  }

  .aggregate-preview :global(li) {
    margin: 0;
    line-height: 1.4;
  }

  .no-aggregates {
    color: var(--color-text-light);
    font-style: italic;
    margin: 0;
    padding: var(--space-md);
    text-align: center;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-xl);
    gap: var(--space-md);
  }

  .error-message {
    color: var(--color-error);
    text-align: center;
    padding: var(--space-lg);
  }

  .retry-button {
    background-color: var(--color-primary);
    color: var(--color-surface);
    border: none;
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--border-radius);
    cursor: pointer;
    margin-top: var(--space-sm);
  }

  .unimplemented {
    color: var(--color-text-light);
    font-style: italic;
    text-align: center;
    padding: var(--space-lg);
    margin: 0;
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
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .filing-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
  }

  .filing-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

  .filing-dates {
    display: flex;
    gap: var(--space-sm);
  }

  .filing-date,
  .period-date {
    display: flex;
    flex-direction: column;
  }

  .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    font-size: 0.8rem;
  }

  .filing-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .accession-number {
    color: var(--color-text-light);
    font-family: monospace;
    font-size: 0.9rem;
  }

  .filing-link {
    color: var(--color-primary);
    font-size: 0.9rem;
    font-weight: var(--font-weight-medium);
    cursor: pointer;
  }

  .link-indicator {
    display: inline-block;
    margin-top: var(--space-xs);
    font-size: 0.8rem;
    color: var(--color-text-light);
  }

  @media (max-width: 768px) {
    .company-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }

    .summary-item {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-xs);
    }
  }
</style>
