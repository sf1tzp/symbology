<script lang="ts">
	import { ChevronLeft, ChevronRight, Sparkles, ScrollText, Star, Plus } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import FilingTimeline from '$lib/components/filings/FilingTimeline.svelte';
	import {
		formatFilingPeriod,
		formatDate,
		getAnalysisTypeDisplay,
		shortModelName
	} from '$lib/utils/filings';
	import {
		formatFinancialValue,
		findConcept,
		getLatestValue,
		getPeriodsRange
	} from '$lib/utils/financials';
	import { toTitleCase } from '$lib/utils';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const company = $derived(data.company);
	const page = $derived(data.companyPageContent);
	const sourceFilings = $derived(data.sourceFilings ?? []);
	const filings = $derived(data.filings ?? []);
	const financialComparison = $derived(data.financialComparison ?? null);

	const companyName = $derived(company?.display_name || company?.name || 'Company');

	// Order change reports to match the canonical 10-K section order.
	const DOC_TYPE_ORDER = [
		'business_description',
		'risk_factors',
		'management_discussion',
		'controls_procedures',
		'market_risk'
	];
	// One accent per document type (theme palette).
	const DOC_COLORS: Record<string, string> = {
		business_description: 'var(--teal-2)',
		risk_factors: 'var(--danger)',
		management_discussion: 'var(--blue)',
		controls_procedures: 'var(--gold)',
		market_risk: 'var(--plum)'
	};
	const docColor = (t: string): string => DOC_COLORS[t] ?? 'var(--ink-3)';

	const changeReports = $derived(
		[...(page?.changeReports ?? [])].sort(
			(a, b) => DOC_TYPE_ORDER.indexOf(a.documentType) - DOC_TYPE_ORDER.indexOf(b.documentType)
		)
	);

	// "What's new" change cards from the latest filing's diffs, ranked by significance.
	const changeCards = $derived(data.changeCards ?? []);
	const CHANGE_KIND_LABEL: Record<string, string> = {
		new: 'New disclosure',
		escalated: 'Escalated',
		de_emphasised: 'De-emphasised',
		reworded: 'Reworded',
		removed: 'Removed'
	};
	const changeKindLabel = (k: string): string => CHANGE_KIND_LABEL[k] ?? k;

	const hasAnalysis = $derived(!!(page && (page.intro?.content || page.main?.content)));
	const _generationDepth = $derived(
		page?.main?.generationDepth ?? page?.intro?.generationDepth ?? null
	);
	const synthesisModelRaw = $derived(page?.main?.model ?? page?.intro?.model ?? null);
	const _synthesisModel = $derived(synthesisModelRaw ? shortModelName(synthesisModelRaw) : null);
	const synthesizedOn = $derived(page?.createdAt);

	// ── Filing-derived stats ──
	const lastFiling = $derived(filings.length > 0 ? filings[filings.length - 1] : null);
	const firstFiling = $derived(filings.length > 0 ? filings[0] : null);
	const trackingSince = $derived(firstFiling ? formatFilingPeriod(firstFiling, company) : null);

	function spanLabel(): string {
		if (sourceFilings.length === 0) return '';
		const periods = sourceFilings
			.map((f) => f.period_of_report ?? f.filing_date)
			.filter(Boolean)
			.sort();
		const first = periods[0]?.slice(0, 4);
		const last = periods[periods.length - 1]?.slice(0, 4);
		return first && last && first !== last ? `FY${first} — FY${last}` : first ? `FY${first}` : '';
	}

	// ── Financial metrics (mirrors the /c/[ticker] overview) ──
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

	const epsItem = $derived(
		financialComparison
			? findConcept(financialComparison.items, ['EarningsPerShare', 'Earnings Per Share'])
			: null
	);
	const epsLatest = $derived(epsItem ? getLatestValue(epsItem) : null);
	const epsChange = $derived(epsItem?.changes.find((c) => c.percent !== null) ?? null);

	const _periodsRange = $derived(financialComparison ? getPeriodsRange(financialComparison) : null);

	function scrollTo(id: string) {
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
	}

	// Full, human-readable timestamp for the "Updated" hover tooltip.
	function fullTimestamp(value: string): string {
		const d = new Date(value);
		return isNaN(d.getTime()) ? value : `${d.toLocaleString()} (${d.toUTCString()})`;
	}
</script>

<svelte:head>
	<title>{companyName} - Symbology</title>
	<meta name="description" content="Company analysis for {companyName}" />
</svelte:head>

<!-- Back link -->
<div class="eyebrow mb-4 hidden md:block">
	<a
		href="/companies"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		All companies
	</a>
</div>

<!-- SECTION 1: Masthead — info left, activations right -->
<section class="company-hero">
	<div>
		<SectionHead
			class="mt-4"
			sticky
			eyebrow="SYMBOLOGY.ONLINE &middot; Company Overview"
			heading=""
		/>
		<h1 class="display" style="margin-bottom: 1.25rem;">
			{toTitleCase(companyName)}<em>.</em>
		</h1>
		{#if page?.intro?.content}
			<p class="lede" style="color: var(--ink-2); max-width: 62ch; margin-bottom: 1.5rem;">
				{page.intro.content}
			</p>
		{/if}
		<div
			style="margin-top: 1.5rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;"
		>
			<span class="tag" style="font-weight: 500; color: var(--ink);">{company?.ticker}</span>
			{#if spanLabel()}<span class="tag">{spanLabel()}</span>{/if}
			{#if hasAnalysis}
				<span class="tag tag-new" style="gap: 4px;">
					<Sparkles class="h-2.5 w-2.5" />
					Multi-Level Synthesis
					<SynthesisHelp />
				</span>
			{/if}
		</div>
	</div>

	<!-- Right: activations placeholder zone -->
	<aside class="activations">
		<div class="activation-row">
			<button type="button" class="activation-btn" disabled title="Coming soon">
				<Star class="h-3.5 w-3.5" />
				Watch
			</button>
			<button type="button" class="activation-btn" disabled title="Coming soon">
				<Plus class="h-3.5 w-3.5" />
				Follow
			</button>
		</div>
		<!-- <a
			href="https://finance.yahoo.com/quote/{company?.ticker}/"
			target="_blank"
			rel="noopener noreferrer"
			class="activation-btn"
		>
			<ExternalLink class="h-3.5 w-3.5" />
			Yahoo Finance
		</a> -->
	</aside>
</section>

<!-- DATA ROW: financial stats strip -->
{#if filings.length > 0}
	<div class="stats" style="margin-top: 2.5rem;">
		{#if revenueLatest}
			<div class="stat">
				<span class="stat-value">${formatFinancialValue(revenueLatest.value)}</span>
				<span class="stat-label">Net Revenue</span>
			</div>
		{/if}
		<div class="stat" onclick={() => scrollTo('filing-timeline')}>
			<span class="stat-value">{filings.length}</span>
			<span class="stat-label">Filings Tracked</span>
		</div>
		{#if lastFiling}
			<div class="stat">
				<span class="stat-value">{lastFiling.form}</span>
				<span class="stat-label">Last Filing &middot; {formatDate(lastFiling.filing_date)}</span>
			</div>
		{/if}
		{#if trackingSince}
			<div class="stat">
				<span class="stat-value">{trackingSince}</span>
				<span class="stat-label">Earliest Filing</span>
			</div>
		{/if}
	</div>
{/if}

{#if hasAnalysis}
	<!-- THE BRIEF: reader-friendly, brief column left / analysis right -->
	{#if page?.main?.content}
		<section style="margin-top: 3rem;">
			<div class="two-col">
				<div class="hidden md:block">
					<div class="eyebrow flex items-center" style="margin-bottom: 12px;">
						<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;THE BRIEF&nbsp;
					</div>
					<p class="brief-meta">
						Synthesised across
						<strong>{sourceFilings.length} filing{sourceFilings.length !== 1 ? 's' : ''}</strong><br
						/>
						{#if spanLabel()}
							from {spanLabel()}
						{/if}.<br />
						{#if synthesizedOn}
							Updated <span class="updated-on" title={fullTimestamp(synthesizedOn)}
								>{formatDate(synthesizedOn)}</span
							>.
						{/if}
					</p>
					<div
						style="margin-top: 1.75rem; display: flex; flex-direction: column; gap: 0.625rem; align-items: flex-start;"
					>
						{#if changeReports.length > 0}
							<button class="brief-link" onclick={() => scrollTo('financials')}>
								Read the complete analysis &rarr;
							</button>
						{/if}
						{#if sourceFilings.length > 0}
							<button class="brief-link subtle" onclick={() => scrollTo('filing-timeline')}>
								View source filings
							</button>
						{/if}
					</div>
				</div>
				<div class="analysis-body">
					<SectionHead
						sticky
						stickyHeading
						eyebrow="SYMBOLOGY.ONLINE l{page.main?.generationDepth} SYNTHESIS"
						heading="The Brief on {toTitleCase(companyName)}."
						synthesisHelp
					/>
					<MarkdownContent class="" content={page.main.content} />
				</div>
			</div>
		</section>
	{/if}

	<!-- FINANCIAL OVERVIEW -->
	{#if financialComparison && financialComparison.items.length > 2}
		<section id="financials" class="hairline-section" style="scroll-margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="{company?.ticker} &middot; FINANCIALS"
				heading="A glance at finances."
			/>
			<div class="two-col-even">
				<div>
					<!-- <div class="eyebrow" style="margin-bottom: 1.125rem;">
						<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{company?.ticker}
						&middot; FINANCIAL METRICS
						{#if periodsRange}&middot; {periodsRange}{/if}
					</div>
					<h2 class="section-heading" style="margin-bottom: 1.125rem;">The financials</h2> -->
					<!-- <p class="body-text" style="color: var(--ink-2);">
						{financialComparison.periods.length} reporting periods tracked across income statement, balance
						sheet, and cash flow data.
					</p> -->
				</div>
				<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0;">
					{#if revenueLatest}
						<div class="stat">
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
						<div class="stat">
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
						<div
							class="stat"
							style="padding: 1rem 0; margin: 1rem 0; border-top: 1px solid var(--rule);"
						>
							<span class="stat-label">Total Assets</span>
							<span class="stat-value">${formatFinancialValue(totalAssetsLatest.value)}</span>
						</div>
					{/if}
					{#if epsLatest}
						<div
							class="stat"
							style="padding: 1rem 0; margin: 1rem 0; border-top: 1px solid var(--rule);"
						>
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
				<div style="flex justify-end">
					<a
						href="/c/{company?.ticker}/financials"
						class="meta no-underline"
						style="color: var(--teal-2);"
					>
						View detailed financials &rarr;
					</a>
				</div>
			</div>
		</section>
	{/if}
	<!-- CHANGE CARDS: one colored card per document type -->
	{#if changeCards.length > 0}
		<section id="whats-new" class="hairline-section" style="scroll-margin-top: 2rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="SYMBOLOGY.ONLINE"
				heading="What's new in the latest filing."
			/>
			<div class="change-grid">
				{#each changeCards as c (c.id)}
					<a
						href="/c/{company?.ticker}/changes/{c.documentType}#diff-{c.id}"
						class="change-card"
						style="--card-accent: {docColor(c.documentType)};"
					>
						<div class="hd">
							<span class="hd-dot" style="background: {docColor(c.documentType)};"></span>
							{getAnalysisTypeDisplay(c.documentType)} · {changeKindLabel(c.changeKind)}
						</div>
						{#if c.heading}
							<div class="ti">{c.heading}</div>
						{/if}
						{#if c.summary}
							<div class="bd">{c.summary}</div>
						{/if}
						<div class="ft">
							{#if c.sectionPath}
								<span class="meta" style="font-family: var(--mono); color: var(--ink-4);"
									>{c.sectionPath}</span
								>
							{:else}
								<span></span>
							{/if}
							<span>Open <ChevronRight class="inline h-3 w-3" /></span>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}

	<!-- CHANGE REPORTS -->
	{#if changeReports.length > 0}
		<section id="change-reports" class="hairline-section" style="scroll-margin-top: 2rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="SYMBOLOGY.ONLINE L2 Synthesis"
				heading="Sections compared over time."
				synthesisHelp
			/>
			<div class="change-grid">
				{#each changeReports as cr (cr.documentType)}
					<a
						href="/c/{company?.ticker}/changes/{cr.documentType}"
						class="change-card"
						style="--card-accent: {docColor(cr.documentType)};"
					>
						<div class="hd">
							<span class="hd-dot" style="background: {docColor(cr.documentType)};"></span>
							{getAnalysisTypeDisplay(cr.documentType)}
						</div>
						{#if cr.intro?.content}
							<div class="bd">{cr.intro.content}</div>
						{:else if cr.report?.content}
							<div class="bd">{cr.report.content.slice(0, 220)}…</div>
						{/if}
						<div class="ft">
							<span
								class="tag"
								style="font-size: 10px; gap: 4px; color: {docColor(
									cr.documentType
								)}; border-color: color-mix(in oklch, {docColor(
									cr.documentType
								)} 40%, transparent);"
							>
								<Sparkles class="h-2.5 w-2.5" />
								L2 Synthesis <SynthesisHelp />
							</span>
							<span>Open <ChevronRight class="inline h-3 w-3" /></span>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}
{:else}
	<div style="text-align: center; padding: 4rem 0;">
		<ScrollText class="mx-auto mb-3 h-6 w-6" style="color: var(--ink-4);" />
		<p class="body-text" style="color: var(--ink-3);">
			No company analysis has been published for {companyName} yet.
		</p>
	</div>
{/if}

<!-- FILING TIMELINE -->
{#if filings.length > 0}
	<section class="hairline-section pb-8" id="filing-timeline">
		<SectionHead sticky stickyHeading eyebrow="FILING HISTORY" heading="View specific filings" />
		<div style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
			<FilingTimeline {filings} {company} linkPrefix="/f" />
		</div>
	</section>
{/if}

<style>
	.company-hero {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 3rem;
		align-items: end;
	}
	@media (max-width: 768px) {
		.company-hero {
			grid-template-columns: 1fr;
			gap: 2rem;
			align-items: start;
		}
		/* Activations span the width and read as full-width buttons on mobile. */
		.activations {
			align-items: stretch;
		}
		.activation-row .activation-btn {
			flex: 1;
		}
		.activation-btn {
			justify-content: center;
		}
	}

	/* Activations placeholder zone */
	.activations {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 0.625rem;
	}
	.activation-row {
		display: flex;
		gap: 0.5rem;
	}
	.activation-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 0.875rem;
		font-size: 13px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--ink-2);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 8px;
		text-decoration: none;
		cursor: pointer;
		transition:
			border-color 0.15s,
			color 0.15s;
	}
	.activation-btn:hover:not(:disabled) {
		border-color: var(--rule-2);
		color: var(--ink);
	}
	.activation-btn:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	/* Brief column */
	.brief-meta {
		font-size: 13px;
		line-height: 1.6;
		color: var(--ink-4);
		max-width: 32ch;
	}
	.brief-meta strong {
		color: var(--ink-2);
		font-weight: 600;
	}
	.brief-link {
		background: none;
		border: none;
		padding: 0;
		font-size: 14px;
		font-family: var(--sans);
		color: var(--teal-2);
		cursor: pointer;
	}
	.brief-link:hover {
		text-decoration: underline;
		text-underline-offset: 3px;
	}
	.brief-link.subtle {
		font-size: 13px;
		color: var(--ink-3);
	}
	.updated-on {
		color: var(--teal-2);
		cursor: help;
		text-decoration: underline dotted;
		text-underline-offset: 2px;
		text-decoration-color: color-mix(in oklch, var(--teal-2) 45%, transparent);
		transition: text-decoration-color 0.15s;
	}
	.updated-on:hover {
		text-decoration-color: var(--teal-2);
	}

	/* Change report cards — left accent per document type */
	.change-grid {
		display: grid;
		/* min(300px, 100%) keeps a single card from forcing overflow on phones
		   narrower than 300px of content. */
		grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
		gap: 1rem;
	}
	.change-card {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--rule);
		border-left: 3px solid var(--card-accent, var(--teal-2));
		border-radius: 0 8px 8px 0;
		text-decoration: none;
		color: inherit;
		transition:
			border-color 0.15s,
			background 0.1s;
	}
	.change-card:hover {
		border-color: var(--rule-2);
		background: var(--paper-2);
	}
	.change-card .hd {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 15px;
		font-weight: 600;
		color: var(--ink);
	}
	.change-card .hd-dot {
		width: 8px;
		height: 8px;
		border-radius: 9999px;
		flex-shrink: 0;
	}
	.change-card .ti {
		font-family: var(--serif);
		font-size: 16px;
		line-height: 1.3;
		color: var(--ink);
	}
	.change-card .bd {
		font-size: 13.5px;
		line-height: 1.55;
		color: var(--ink-3);
	}
	.change-card .ft {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: auto;
		padding-top: 0.5rem;
		font-size: 12px;
		color: var(--ink-4);
	}
</style>
