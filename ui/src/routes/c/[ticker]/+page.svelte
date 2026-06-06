<script lang="ts">
	import { ChevronLeft, Sparkles, Star, Plus } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import FilingTimeline from '$lib/components/filings/FilingTimeline.svelte';
	import PendingContentNotice from '$lib/components/PendingContentNotice.svelte';
	import ChangeCard from '$lib/components/ChangeCard.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import { docColor, changeKindColor } from '$lib/utils/changes';
	import { formatDate, getAnalysisTypeDisplay, shortModelName } from '$lib/utils/filings';
	import { formatHeadlineStat, pickHeadlineStats, getPeriodsRange } from '$lib/utils/financials';
	import { previewContent, toTitleCase } from '$lib/utils';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const company = $derived(data.company);
	const page = $derived(data.companyPageContent);
	const sourceFilings = $derived(data.sourceFilings ?? []);
	const sourceInputTokens = $derived(data.sourceInputTokens ?? 0);
	const filings = $derived(data.filings ?? []);
	const financialComparison = $derived(data.financialComparison ?? null);

	// Which form's page is being shown, and the forms a reader can toggle between.
	// The 10-Q page reads in plum; the 10-K page (default) stays teal.
	const selectedForm = $derived(data.selectedForm ?? '10-K');
	const availableForms = $derived(data.availableForms ?? []);
	const accent = $derived(selectedForm === '10-Q' ? 'var(--plum)' : 'var(--teal-2)');
	// Carry the selected form onto change-report sub-page links (10-K is the default,
	// so it needs no query param).
	const formQuery = $derived(selectedForm === '10-K' ? '' : `?form=${selectedForm}`);

	const companyName = $derived(company?.display_name || company?.name || 'Company');

	// Order change reports to match the canonical 10-K section order.
	const DOC_TYPE_ORDER = [
		'business_description',
		'risk_factors',
		'management_discussion',
		'controls_procedures',
		'market_risk'
	];
	const changeReports = $derived(
		[...(page?.changeReports ?? [])].sort(
			(a, b) => DOC_TYPE_ORDER.indexOf(a.documentType) - DOC_TYPE_ORDER.indexOf(b.documentType)
		)
	);

	// "What's new" change cards from the latest filing's diffs, ranked by significance.
	const changeCards = $derived(data.changeCards ?? []);

	const hasAnalysis = $derived(!!(page && (page.intro?.content || page.main?.content)));
	const _generationDepth = $derived(
		page?.main?.generationDepth ?? page?.intro?.generationDepth ?? null
	);
	const synthesisModelRaw = $derived(page?.main?.model ?? page?.intro?.model ?? null);
	const _synthesisModel = $derived(synthesisModelRaw ? shortModelName(synthesisModelRaw) : null);
	const synthesizedOn = $derived(page?.createdAt);

	// ── Filing-derived stats ──
	// Fallback for pending companies (diffs but no synthesis yet, so no source filings).
	const lastFiling = $derived(filings.length > 0 ? filings[filings.length - 1] : null);

	// The dominant form type across the synthesis's source filings (e.g. "10-K").
	const sourceForm = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const f of sourceFilings) counts[f.form] = (counts[f.form] ?? 0) + 1;
		let best: string | null = null;
		let bestN = 0;
		for (const [form, n] of Object.entries(counts)) {
			if (n > bestN) {
				best = form;
				bestN = n;
			}
		}
		return best;
	});

	// Compact token count, e.g. 1,240,000 → "1.2M", 84,300 → "84K".
	function formatTokens(n: number): string {
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
		if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
		return `${n}`;
	}

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

	// ── Financial metrics ──
	// Prioritised headline stats, resolved against whatever statements this company
	// actually reports — so a company missing one statement (e.g. banks/REITs with
	// no parseable income statement) still fills the strip instead of looking empty.
	const headlineStats = $derived(pickHeadlineStats(financialComparison, 4));
	// The single lead stat for the masthead data row (Net Revenue for most, else
	// the company's top reported metric, e.g. Total Assets for a bank).
	const leadStat = $derived(headlineStats[0] ?? null);

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
			{accent}
			eyebrow="SYMBOLOGY.ONLINE &middot; Company Overview"
			heading=""
		/>
		<h1 class="display" style="margin-bottom: 1.25rem;">
			{toTitleCase(companyName)}<em>.</em>
		</h1>
		{#if company.sic_description}
			<div
				class="mb-4 font-serif text-xs text-ink-3 italic"
				style="margin-top: 2px; color: var(--ink-4);"
			>
				{company.sic_description}
			</div>
		{/if}
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
				<span class="tag tag-new flex gap-2">
					<Sparkles class="h-2.5 w-2.5" />
					Multi-Level Synthesis
					<SynthesisHelp />
				</span>
			{/if}
			{#if availableForms.length > 1}
				<!-- Switch between the 10-K- and 10-Q-derived pages. Anchor links so the
				     server load re-runs for the chosen form (and works without JS). -->
				<span class="form-toggle" role="group" aria-label="Filing form">
					{#each availableForms as f (f)}
						<a
							href="?form={f}"
							class="form-toggle-opt"
							class:active={selectedForm === f}
							style={selectedForm === f && f === '10-Q' ? 'color: var(--plum);' : ''}
							aria-current={selectedForm === f ? 'true' : undefined}
						>
							{f}
						</a>
					{/each}
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
		{#if leadStat}
			<div class="stat">
				<span class="stat-value">
					{formatHeadlineStat(leadStat)}
					{#if leadStat.change?.percent}
						<span
							class="stat-delta"
							style="color: {leadStat.change.percent > 0 ? 'var(--teal-2)' : 'var(--danger)'};"
						>
							{leadStat.change.percent > 0 ? '+' : ''}{leadStat.change.percent.toFixed(1)}%
						</span>
					{/if}
				</span>
				<span class="stat-label">{leadStat.label}</span>
			</div>
		{/if}
		{#if spanLabel()}
			<div class="stat gold" onclick={() => scrollTo('filing-timeline')}>
				<span class="stat-value">{spanLabel()}</span>
				<span class="stat-label">Synthesis Period</span>
			</div>
		{/if}
		{#if sourceForm}
			<div class="stat">
				<span class="stat-value">{sourceForm}</span>
				<span class="stat-label">Synthesised from Form {sourceForm}</span>
			</div>
		{:else if lastFiling}
			<div class="stat">
				<span class="stat-value">{lastFiling.form}</span>
				<span class="stat-label">Last Filing &middot; {formatDate(lastFiling.filing_date)}</span>
			</div>
		{/if}
		{#if sourceInputTokens > 0}
			<div class="stat">
				<span class="stat-value">{formatTokens(sourceInputTokens)}</span>
				<span class="stat-label">Input Tokens Considered</span>
			</div>
		{/if}
	</div>
{/if}

<!-- THE BRIEF: reader-friendly, brief column left / analysis right -->
{#if page?.main?.content}
	<section style="margin-top: 3rem;">
		<div class="two-col">
			<div class="hidden md:block">
				<div class="eyebrow flex items-center" style="margin-bottom: 12px;">
					<span style="color: {accent};">&#9679;</span>&nbsp;&nbsp;THE BRIEF&nbsp;
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
					{accent}
					eyebrow="SYMBOLOGY.ONLINE l{page.main?.generationDepth} SYNTHESIS"
					heading="The Brief on {toTitleCase(companyName)}."
					synthesisHelp
				/>
				<MarkdownContent class="" content={page.main.content} />
			</div>
		</div>
	</section>
{:else}
	<section style="margin-top: 3rem;">
		<PendingContentNotice label="brief" subject={toTitleCase(companyName)} />
	</section>
{/if}

<!-- FINANCIAL OVERVIEW -->
{#if headlineStats.length > 0}
	<section id="financials" class="hairline-section" style="scroll-margin-top: 3rem;">
		<SectionHead
			sticky
			stickyHeading
			{accent}
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
				{#each headlineStats as stat, i (stat.label)}
					<div
						class="stat"
						style={i >= 2
							? 'padding: 1rem 0; margin: 1rem 0; border-top: 1px solid var(--rule);'
							: ''}
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
			<div style="flex justify-end">
				<a
					href="/c/{company?.ticker}/financials{formQuery}"
					class="meta no-underline"
					style="color: var(--teal-2);"
				>
					View detailed financials &rarr;
				</a>
			</div>
		</div>
	</section>
{/if}

<!-- FILING TIMELINE -->
{#if filings.length > 0}
	<section class="hairline-section pb-8" id="filing-timeline">
		<SectionHead
			sticky
			stickyHeading
			{accent}
			eyebrow="FILING HISTORY"
			heading="View specific filings"
		/>
		<FilingTimeline {filings} {company} linkPrefix="/f" />
	</section>
{/if}

<!-- CHANGE REPORTS -->
{#if changeReports.length > 0}
	<section id="change-reports" class="hairline-section" style="scroll-margin-top: 2rem;">
		<SectionHead
			sticky
			stickyHeading
			{accent}
			eyebrow="SYMBOLOGY.ONLINE L2 Synthesis"
			heading="Sections compared over time."
			synthesisHelp
		/>
		<div class="change-grid">
			{#each changeReports as cr (cr.documentType)}
				<ChangeCard
					href="/c/{company?.ticker}/changes/{cr.documentType}{formQuery}"
					accent={docColor(cr.documentType)}
					summary={cr.intro?.content
						? previewContent(cr.intro.content, 1)
						: cr.report?.content
							? `${previewContent(cr.report.content)}…`
							: null}
				>
					{#snippet header()}
						{getAnalysisTypeDisplay(cr.documentType)}
					{/snippet}
					{#snippet footerLeft()}
						<span
							class="tag"
							style="font-size: 10px; gap: 4px; color: {docColor(
								cr.documentType
							)}; border-color: color-mix(in oklch, {docColor(cr.documentType)} 40%, transparent);"
						>
							<Sparkles class="h-2.5 w-2.5" />
							L2 Synthesis <SynthesisHelp />
						</span>
					{/snippet}
				</ChangeCard>
			{/each}
		</div>
	</section>
{/if}

<!-- CHANGE CARDS: one colored card per document type -->
{#if changeCards.length > 0}
	<section id="whats-new" class="hairline-section" style="scroll-margin-top: 2rem;">
		<SectionHead
			sticky
			stickyHeading
			{accent}
			diffHelp={true}
			eyebrow="SYMBOLOGY.ONLINE TEXT DIFFS"
			heading="What's new in the latest filing."
		/>
		<div class="change-grid">
			{#each changeCards as c (c.id)}
				<ChangeCard
					href="/c/{company?.ticker}/changes/{c.documentType}{formQuery}#diff-{c.id}"
					accent={changeKindColor(c.changeKind)}
					dot={false}
					heading={c.heading}
					summary={c.summary}
				>
					{#snippet header()}
						<div class="flex w-full justify-between">
							<p class="text-sm text-ink">
								<em>In the {getAnalysisTypeDisplay(c.documentType)}:</em>
							</p>
							<p>
								<ChangeKindTag changeKind={c.changeKind} />
							</p>
						</div>
					{/snippet}
					{#snippet footerLeft()}
						{#if c.sectionPath}
							<span class="meta" style="font-family: var(--mono); color: var(--ink-4);"
								>{c.sectionPath}</span
							>
						{/if}
					{/snippet}
				</ChangeCard>
			{/each}
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

	/* 10-K / 10-Q page toggle in the masthead tag row. */
	.form-toggle {
		display: inline-flex;
		gap: 2px;
		padding: 2px;
		background: var(--paper-2);
		border: 1px solid var(--rule);
		border-radius: 8px;
	}
	.form-toggle-opt {
		padding: 3px 10px;
		border-radius: 6px;
		font-family: var(--mono);
		font-size: 11px;
		letter-spacing: 0.02em;
		color: var(--ink-3);
		text-decoration: none;
		transition:
			background 0.12s,
			color 0.12s;
	}
	.form-toggle-opt:hover {
		color: var(--ink);
	}
	.form-toggle-opt.active {
		background: var(--paper);
		color: var(--ink);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	/* Year-over-year delta on the lead financial stat in the data row. */
	.stat-delta {
		font-family: var(--mono);
		font-size: 0.875rem;
		letter-spacing: -0.01em;
		margin-left: 0.35rem;
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
</style>
