<script lang="ts">
	import { ChevronLeft } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import FinancialTable from '$lib/components/financials/FinancialTable.svelte';
	import type { PageData } from './$types';
	import {
		formatHeadlineStat,
		pickHeadlineStats,
		getPeriodsRange,
		statementItemCounts,
		firstNonEmptyStatement
	} from '$lib/utils/financials';
	import { formatDate } from '$lib/utils/filings';

	let { data }: { data: PageData } = $props();

	const ticker = $derived(data.ticker);
	const company = $derived(data.company);
	const financialComparison = $derived(data.financialComparison);
	const filings = $derived(data.filings || []);

	// Match the form the reader came from: plum accent + back-link on the 10-Q page.
	const selectedForm = $derived(data.selectedForm ?? '10-K');
	const accent = $derived(selectedForm === '10-Q' ? 'var(--plum)' : 'var(--teal-2)');
	const formQuery = $derived(selectedForm === '10-K' ? '' : `?form=${selectedForm}`);

	const displayName = $derived(company?.display_name || company?.name || `${ticker} Company`);

	const periodsRange = $derived(financialComparison ? getPeriodsRange(financialComparison) : null);

	const lastFiling = $derived(filings.length > 0 ? filings[filings.length - 1] : null);

	// Prioritised headline stats, resolved against whatever statements this company
	// reports (see pickHeadlineStats) — fills the strip even when one statement is
	// missing instead of leaving income-statement-only gaps.
	const headlineStats = $derived(pickHeadlineStats(financialComparison, 4));

	// Statement type tabs. A tab is disabled when the company reports nothing under
	// it, and the default tab is the first one that actually has data — so a company
	// with no income statement opens on its balance sheet instead of a blank table.
	const statementTypes = [
		{ key: 'income_statement', label: 'Income Statement' },
		{ key: 'balance_sheet', label: 'Balance Sheet' },
		{ key: 'cash_flow', label: 'Cash Flow' }
	];
	const stmtCounts = $derived(statementItemCounts(financialComparison));
	const defaultStatement = $derived(
		firstNonEmptyStatement(financialComparison) ?? 'income_statement'
	);
	let activeStatementType = $state('income_statement');
	// Snap the active tab to the first non-empty statement once data resolves (and
	// whenever it changes), unless the user has already picked a populated tab.
	$effect(() => {
		if ((stmtCounts[activeStatementType] ?? 0) === 0) activeStatementType = defaultStatement;
	});
</script>

<svelte:head>
	<title>Financials — {displayName} ({ticker}) - Symbology</title>
	<meta name="description" content="Financial metrics and statements for {displayName}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/c/{ticker}{formQuery}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{displayName}
	</a>
</div>

<!-- Hero -->
<section class="two-col-even" style="align-items: end;">
	<div>
		<div class="eyebrow" style="margin-bottom: 1.125rem;">
			<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{ticker}
			&middot; FINANCIAL METRICS
			{#if periodsRange}&middot; {periodsRange}{/if}
		</div>
		<h1 class="display" style="margin-bottom: 1.125rem;">Financial overview</h1>
		<p class="lede">
			{#if financialComparison && financialComparison.periods.length > 0}
				{financialComparison.periods.length} reporting periods tracked across income statement, balance
				sheet, and cash flow data.
			{:else}
				Financial data for {displayName}.
			{/if}
		</p>
	</div>
	<div>
		{#if headlineStats.length > 0}
			<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0;">
				{#each headlineStats as stat, i (stat.label)}
					<div
						class="stat"
						style="padding: 1rem 0;{i >= 2 ? ' border-top: 1px solid var(--rule);' : ''}"
					>
						<span class="stat-label">{stat.label}</span>
						<span class="stat-value">{formatHeadlineStat(stat)}</span>
						{#if stat.change?.percent}
							<span
								class="meta"
								style="color: {stat.change.percent > 0 ? 'var(--teal-2)' : 'var(--danger)'};"
							>
								{stat.change.percent > 0 ? '+' : ''}{stat.change.percent.toFixed(1)}% YoY
							</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</section>

<!-- Financials Table -->
{#if financialComparison && financialComparison.items.length > 0}
	<section class="hairline-section">
		<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
			<div>
				<div class="eyebrow" style="margin-bottom: 10px;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;FINANCIAL STATEMENTS
				</div>
				<h2 class="section-heading">The numbers, in full.</h2>
			</div>
			<div style="display: flex; gap: 0.5rem;">
				{#each statementTypes as st (st.key)}
					{@const empty = (stmtCounts[st.key] ?? 0) === 0}
					<button
						class="statement-tab {activeStatementType === st.key ? 'active' : ''}"
						disabled={empty}
						title={empty ? 'Not reported by this company' : undefined}
						onclick={() => (activeStatementType = st.key)}
					>
						{st.label}
					</button>
				{/each}
			</div>
		</div>

		<FinancialTable financialData={financialComparison} statementType={activeStatementType} />

		<div style="display: flex; justify-content: space-between; margin-top: 1.125rem;">
			<span class="meta">Source: SEC Form 10-K + 10-Q &middot; GAAP</span>
			{#if lastFiling}
				<span class="meta">Latest filing: {formatDate(lastFiling.filing_date)}</span>
			{/if}
		</div>
	</section>
{:else}
	<section class="hairline-section">
		<SectionHead {accent} eyebrow="FINANCIAL STATEMENTS" heading="Financial data" />
		<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
			No financial data available yet for this company.
		</p>
	</section>
{/if}

<!-- Chart placeholders (layerchart integration follow-up) -->
<!-- TODO: Revenue Chart (quarterly bar chart with YoY comparison) -->
<!-- TODO: Margin Chart (line: gross/operating/net) + Segment Donut -->

<!-- Footer -->
<footer
	style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule); color: var(--ink-4);"
>
	<div class="meta">
		{#if lastFiling}
			Data from SEC filings through {formatDate(lastFiling.filing_date)}
		{:else}
			Source: SEC EDGAR
		{/if}
	</div>
</footer>

<style>
	.statement-tab {
		font-family: var(--mono);
		font-size: 0.6875rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
		border: 1px solid var(--rule);
		background: transparent;
		color: var(--ink-2);
		transition:
			border-color 0.15s,
			background 0.15s,
			color 0.15s;
	}
	.statement-tab:hover:not(:disabled) {
		border-color: var(--ink-4);
	}
	.statement-tab:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.statement-tab.active {
		background: var(--ink);
		color: var(--paper);
		border-color: var(--ink);
	}
</style>
