<script lang="ts">
	import { ChevronLeft } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import FinancialTable from '$lib/components/financials/FinancialTable.svelte';
	import type { PageData } from './$types';
	import {
		formatFinancialValue,
		findConcept,
		getLatestValue,
		getPeriodsRange
	} from '$lib/utils/financials';
	import { formatDate } from '$lib/utils/filings';

	let { data }: { data: PageData } = $props();

	const ticker = $derived(data.ticker);
	const company = $derived(data.company);
	const financialComparison = $derived(data.financialComparison);
	const filings = $derived(data.filings || []);

	const displayName = $derived(company?.display_name || company?.name || `${ticker} Company`);

	const periodsRange = $derived(financialComparison ? getPeriodsRange(financialComparison) : null);

	const lastFiling = $derived(filings.length > 0 ? filings[filings.length - 1] : null);

	// Derive headline stats from financial data
	const revenueItem = $derived(
		financialComparison
			? findConcept(
					financialComparison.items,
					['Revenue', 'Net Sales', 'Sales'],
					'income_statement'
				)
			: null
	);
	const revenueLatest = $derived(revenueItem ? getLatestValue(revenueItem) : null);
	const revenueChange = $derived(revenueItem?.changes.find((c) => c.percent !== null) ?? null);

	const epsItem = $derived(
		financialComparison
			? findConcept(financialComparison.items, ['EarningsPerShare', 'Earnings Per Share'])
			: null
	);
	const epsLatest = $derived(epsItem ? getLatestValue(epsItem) : null);
	const epsChange = $derived(epsItem?.changes.find((c) => c.percent !== null) ?? null);

	const netIncomeItem = $derived(
		financialComparison
			? findConcept(financialComparison.items, ['NetIncome', 'Net Income'], 'income_statement')
			: null
	);
	const netIncomeLatest = $derived(netIncomeItem ? getLatestValue(netIncomeItem) : null);
	const netIncomeChange = $derived(netIncomeItem?.changes.find((c) => c.percent !== null) ?? null);

	const totalAssetsItem = $derived(
		financialComparison ? findConcept(financialComparison.items, ['Assets'], 'balance_sheet') : null
	);
	const totalAssetsLatest = $derived(totalAssetsItem ? getLatestValue(totalAssetsItem) : null);

	// Statement type tabs
	let activeStatementType = $state('income_statement');
	const statementTypes = [
		{ key: 'income_statement', label: 'Income Statement' },
		{ key: 'balance_sheet', label: 'Balance Sheet' },
		{ key: 'cash_flow', label: 'Cash Flow' }
	];
</script>

<svelte:head>
	<title>Financials — {displayName} ({ticker}) - Symbology</title>
	<meta name="description" content="Financial metrics and statements for {displayName}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/c/{ticker}"
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
		{#if financialComparison && financialComparison.items.length > 0}
			<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0;">
				{#if revenueLatest}
					<div class="stat" style="padding: 1rem 0;">
						<span class="stat-label">Net Revenue</span>
						<span class="stat-value">${formatFinancialValue(revenueLatest.value)}</span>
						{#if revenueChange?.percent}
							<span
								class="meta"
								style="color: {revenueChange.percent > 0 ? 'var(--teal-2)' : 'var(--danger)'};"
							>
								{revenueChange.percent > 0 ? '+' : ''}{revenueChange.percent.toFixed(1)}% YoY
							</span>
						{/if}
					</div>
				{/if}
				{#if netIncomeLatest}
					<div class="stat" style="padding: 1rem 0;">
						<span class="stat-label">Net Income</span>
						<span class="stat-value">${formatFinancialValue(netIncomeLatest.value)}</span>
						{#if netIncomeChange?.percent}
							<span
								class="meta"
								style="color: {netIncomeChange.percent > 0 ? 'var(--teal-2)' : 'var(--danger)'};"
							>
								{netIncomeChange.percent > 0 ? '+' : ''}{netIncomeChange.percent.toFixed(1)}% YoY
							</span>
						{/if}
					</div>
				{/if}
				{#if totalAssetsLatest}
					<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
						<span class="stat-label">Total Assets</span>
						<span class="stat-value">${formatFinancialValue(totalAssetsLatest.value)}</span>
					</div>
				{/if}
				{#if epsLatest}
					<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
						<span class="stat-label">EPS (Diluted)</span>
						<span class="stat-value">${epsLatest.value.toFixed(2)}</span>
						{#if epsChange?.percent}
							<span
								class="meta"
								style="color: {epsChange.percent > 0 ? 'var(--teal-2)' : 'var(--danger)'};"
							>
								{epsChange.percent > 0 ? '+' : ''}{epsChange.percent.toFixed(1)}% YoY
							</span>
						{/if}
					</div>
				{/if}
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
					<button
						class="statement-tab {activeStatementType === st.key ? 'active' : ''}"
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
		<SectionHead eyebrow="FINANCIAL STATEMENTS" heading="Financial data" />
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
	.statement-tab:hover {
		border-color: var(--ink-4);
	}
	.statement-tab.active {
		background: var(--ink);
		color: var(--paper);
		border-color: var(--ink);
	}
</style>
