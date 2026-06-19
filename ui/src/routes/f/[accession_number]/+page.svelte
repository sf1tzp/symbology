<script lang="ts">
	import { ChevronLeft, ChevronRight, ExternalLink, Sparkles, ScrollText } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import ChangeCard from '$lib/components/ChangeCard.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import DiffRow from '$lib/components/DiffRow.svelte';
	import { changeKindColor, topChangeCards, isVisibleTopic } from '$lib/utils/changes';
	import {
		formatFilingPeriodLong,
		formatDate,
		getAnalysisTypeDisplay,
		shortModelName
	} from '$lib/utils/filings';
	import type { PageData } from './$types';
	import FilingTimeline from '$lib/components/filings/FilingTimeline.svelte';
	import { toTitleCase } from '$lib/utils';

	let { data }: { data: PageData } = $props();

	const company = $derived(data.company);
	const filing = $derived(data.filing);
	const documents = $derived(data.documents || []);
	const filingPageContent = $derived(data.filingPageContent);
	const timeline = $derived(data.timeline || []);
	// Structured diffs of this filing vs. the immediately prior one, per section.
	const priorDiffSets = $derived(data.priorDiffSets ?? []);

	// "What's new" headline cards — the most significant escalated / de-emphasised
	// / reworded shifts in this filing vs. the prior one, across all sections.
	// Mirrors the company page's "What's new" cards (accent per document type).
	const changeCards = $derived(
		topChangeCards(
			priorDiffSets.flatMap((ds) => ds.topics.map((t) => ({ ...t, documentType: ds.documentType })))
		)
	);

	const companyName = $derived(company?.display_name || company?.name || 'Company');
	const fiscalPeriodLong = $derived(filing ? formatFilingPeriodLong(filing, company) : '');

	function getFormLabel(form: string): string {
		if (form.includes('10-K')) return 'ANNUAL REPORT';
		if (form.includes('10-Q')) return 'QUARTERLY REPORT';
		if (form.includes('8-K')) return 'CURRENT REPORT';
		if (form.includes('DEF 14A')) return 'PROXY STATEMENT';
		return form;
	}

	// ── Filing synthesis (analysis) metadata + stats ──
	function wordCount(text: string | null | undefined): number {
		if (!text) return 0;
		return text.trim().split(/\s+/).filter(Boolean).length;
	}
	function formatCount(n: number): string {
		if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`;
		return String(n);
	}

	// "What's new" cards deep-link to the on-page diff in the Compare section.
	// Each diff is its own collapsed <details id="diff-{id}">, so open it and
	// scroll it into view.
	function openDiff(e: MouseEvent, topicId: string) {
		e.preventDefault();
		const el = document.getElementById(`diff-${topicId}`);
		if (el instanceof HTMLDetailsElement) el.open = true;
		requestAnimationFrame(() => {
			el?.scrollIntoView({ behavior: 'smooth' });
			history.replaceState(null, '', `#diff-${topicId}`);
		});
	}

	const hasAnalysis = $derived(
		!!(filingPageContent && (filingPageContent.intro?.content || filingPageContent.main?.content))
	);
	const analysisWords = $derived(
		wordCount(filingPageContent?.main?.content) + wordCount(filingPageContent?.intro?.content)
	);
	const analysisReadMinutes = $derived(Math.max(1, Math.round(analysisWords / 200)));
	const generationDepth = $derived(
		filingPageContent?.main?.generationDepth ?? filingPageContent?.intro?.generationDepth ?? null
	);
	const synthesisModelRaw = $derived(
		filingPageContent?.main?.model ?? filingPageContent?.intro?.model ?? null
	);
	const synthesisModel = $derived(synthesisModelRaw ? shortModelName(synthesisModelRaw) : null);
	const synthesisHash = $derived(
		filingPageContent?.main?.contentHash ?? filingPageContent?.intro?.contentHash ?? null
	);
	const synthesizedOn = $derived(filingPageContent?.createdAt);

	const metadataRows = $derived(
		filing
			? ([
					['Form type', `${filing.form} · ${getFormLabel(filing.form).toLowerCase()}`],
					['Filed', formatDate(filing.filing_date)],
					...(hasAnalysis
						? [
								...(synthesizedOn
									? [['Synthesized', formatDate(synthesizedOn)] as [string, string]]
									: []),
								...(synthesisModel
									? [['Synthesis Model', synthesisModel] as [string, string]]
									: []),
								['Synthesis Level', `L${generationDepth ?? '—'}`] as [string, string],
								...(synthesisHash
									? [['Synthesis Hash', synthesisHash.substring(0, 12)] as [string, string]]
									: [])
							]
						: [])
				] as [string, string][])
			: []
	);

	const monoFields = new Set([
		'CIK',
		'Filed',
		'Period of report',
		'Synthesis Hash',
		'Synthesis Model',
		'Synthesis Level'
	]);
</script>

<svelte:head>
	<title>Filing {data.filing?.form || 'Unknown'} - {companyName} - Symbology</title>
	<meta name="description" content="SEC filing details for {companyName}" />
</svelte:head>

<!-- Back link -->
<div class="eyebrow hidden md:block" style="margin-bottom: 3rem;">
	<a
		href="/c/{company?.ticker}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{companyName}
	</a>
</div>

{#if filing}
	<!-- SECTION 1: Hero with metadata sidebar -->
	<section class="filing-hero">
		<!-- Left column -->
		<div>
			<SectionHead
				sticky
				eyebrow="{getFormLabel(filing.form)} &middot; FORM {filing.form}"
				heading=""
			/>
			<h1 class="display" style="margin-bottom: 1.25rem;">
				{toTitleCase(companyName)},<br />
				<em>{fiscalPeriodLong}.</em>
			</h1>
			{#if filingPageContent && filingPageContent.intro?.content}
				<p class="lede" style="color: var(--ink-2); max-width: 60ch; margin-bottom: 1.5rem;">
					{filingPageContent.intro.content}
				</p>
			{/if}
			<div
				style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;"
			>
				<span class="tag" style="font-family: var(--mono);">
					Accession {filing.accession_number}
				</span>
				{#if documents.length > 0}
					<span class="tag tag-new">
						{documents.length} sections analysed
					</span>
				{/if}
				{#if !hasAnalysis}
					<span class="tag flex gap-2">
						<Sparkles class="h-2.5 w-2.5" />
						Synthesis Queued
					</span>
				{/if}
			</div>
		</div>

		<!-- Right column: Metadata card -->
		<aside class="metadata-card hidden md:block">
			<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1.25rem;">
				Filing metadata
			</h4>
			<div style="display: flex; flex-direction: column; gap: 0.875rem;">
				{#each metadataRows as [k, v] (k)}
					<div style="display: flex; justify-content: space-between; gap: 1rem;">
						<span class="meta flex items-center gap-1" style="color: var(--ink-4);">
							{k}
							{#if k === 'Synthesis Level'}<SynthesisHelp />{/if}
						</span>
						<span
							class="meta"
							style="color: var(--ink-2); text-align: right; font-family: {monoFields.has(k)
								? 'var(--mono)'
								: 'var(--sans)'};">{v}</span
						>
					</div>
				{/each}
			</div>

			{#if hasAnalysis}
				<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.25rem 0;" />
				<div class="meta-stats">
					<div class="meta-stat">
						<div class="meta-stat-value" style="color: var(--teal-2);">
							{formatCount(analysisWords)}
						</div>
						<div class="meta-stat-label">Analysis words</div>
					</div>
					<div class="meta-stat">
						<div class="meta-stat-value" style="color: var(--teal-2);">
							{analysisReadMinutes}<span style="font-size: 1rem;">m</span>
						</div>
						<div class="meta-stat-label">Est. read</div>
					</div>
				</div>
			{/if}

			{#if filing.url}
				<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.25rem 0;" />
				<a href={filing.url} target="_blank" rel="noopener noreferrer" class="btn-filing-primary">
					View on SEC.gov
					<ExternalLink class="h-3.5 w-3.5" />
				</a>
			{/if}
		</aside>
	</section>

	<!-- SECTION: Filing analysis (structured page content) -->
	{#if filingPageContent && (filingPageContent.intro?.content || filingPageContent.main?.content)}
		<section class="hairline-section">
			<div class="analysis-layout">
				<!-- Source-document sidebar -->
				<aside class="analysis-toc hidden md:block">
					<h3 class="sub" style="margin-bottom: 14px;">Synthesis Sources</h3>
					<div style="display: flex; flex-direction: column; gap: 14px;">
						{#each documents as doc (doc.id)}
							{#if doc.has_analysis}
								<a
									href="/d/{filing.accession_number}/{doc.short_hash}"
									style="text-decoration: none;"
								>
									<div style="font-size: 15px; color: var(--ink); font-family: var(--serif);">
										{getAnalysisTypeDisplay(doc.document_type)}
									</div>
									<div
										class="meta text-xs"
										style="color: {doc.has_analysis ? 'var(--teal-2)' : 'var(--ink-4)'};"
									>
										{doc.has_analysis ? 'L1 Synthesis' : 'Source Document'}
									</div>
								</a>
							{/if}
						{/each}
					</div>
				</aside>

				<article>
					<SectionHead
						sticky
						stickyHeading
						eyebrow="SYMBOLOGY.ONLINE l{filingPageContent.main?.generationDepth} SYNTHESIS"
						heading="{company?.ticker} &middot; Form {filing.form} Analysis"
						synthesisHelp
					/>

					{#if filingPageContent.main?.content}
						<div class="body-text" style="color: var(--ink-2);">
							<MarkdownContent content={filingPageContent.main.content} />
						</div>
					{/if}

					{#if filingPageContent.main?.generationDepth != null}
						<div style="margin-top: 1.5rem;">
							<span class="tag" style="font-family: var(--mono); font-size: 10px; gap: 4px;">
								<Sparkles class="h-2.5 w-2.5" />
								Generated · depth {filingPageContent.main.generationDepth}
							</span>
						</div>
					{/if}
				</article>
			</div>
		</section>
	{/if}

	<!-- SECTION: What's new (headline change cards) -->
	{#if changeCards.length > 0}
		<section class="hairline-section">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="SYMBOLOGY.ONLINE &middot; text diffs"
				heading="What's changed since the last filing."
				diffHelp
			/>
			<div class="change-grid">
				{#each changeCards as c (c.id)}
					<ChangeCard
						href="#diff-{c.id}"
						onclick={(e) => openDiff(e, c.id)}
						accent={changeKindColor(c.changeKind)}
						dot={false}
						heading={c.heading}
						summary={c.summary}
					>
						{#snippet header()}
							<div class="flex w-full justify-between">
								<p><em>In the {getAnalysisTypeDisplay(c.documentType)}:</em></p>
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

	<!-- FILING TIMELINE -->
	{#if timeline}
		<section class="hairline-section" id="filing-timeline">
			<SectionHead sticky stickyHeading eyebrow="FILING HISTORY" heading="View specific filings" />
			<div style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
				<FilingTimeline filings={timeline} {company} selectedId={filing.id} linkPrefix="/f" />
			</div>
		</section>
	{/if}

	<!-- SECTION 2: Documents -->
	<section class="hairline-section">
		<SectionHead
			sticky
			stickyHeading
			eyebrow="DOCUMENTS"
			heading="{documents.length} filing document{documents.length !== 1 ? 's' : ''}, in order."
		/>

		{#if documents.length > 0}
			<div style="border: 1px solid var(--rule); border-radius: 8px; overflow: hidden;">
				{#each documents as doc, i (doc.id)}
					<a href="/d/{filing.accession_number}/{doc.short_hash}" class="docrow-filing">
						<div class="meta text-xs" style="color: var(--ink-3);">&sect;{i + 1}</div>
						<div>
							<div class="text-lg font-[450] text-ink-2">
								{getAnalysisTypeDisplay(doc.document_type)}
							</div>
							<!-- <div class="meta" style="margin-top: 2px; color: var(--ink-4);">
								{doc.document_type}
							</div> -->
						</div>
						<div>
							{#if doc.has_analysis}
								<span class="tag tag-new" style="font-size: 10px; gap: 4px;">
									<Sparkles class="h-2.5 w-2.5" />
								</span>
							{/if}
							<span class="tag hidden text-olive md:inline-flex" style="font-size: 10px; gap: 4px;">
								<ScrollText class="h-2.5 w-2.5" />
								Source Document
							</span>
						</div>
						<div>
							<ChevronRight class="h-3.5 w-3.5" style="color: var(--ink-4);" />
						</div>
					</a>
				{/each}
			</div>
		{:else}
			<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
				No documents found in this filing.
			</p>
		{/if}
	</section>

	<!-- SECTION 3: Compare with the prior filing -->
	{#if priorDiffSets.length > 0}
		<section class="hairline-section">
			{#each priorDiffSets as ds (ds.id)}
				<SectionHead
					sticky
					stickyHeading
					eyebrow="symbology.online &middot; text diffs"
					heading="Side-by-side against the prior {getAnalysisTypeDisplay(ds.documentType)}."
					diffHelp
				/>
				{@const changed = ds.topics.filter(isVisibleTopic)}
				{#if changed.length > 0}
					<div class="diff-group">
						<div class="diff-group-head">
							<h3 class="diff-group-title">{getAnalysisTypeDisplay(ds.documentType)}</h3>
							<span class="meta" style="color: var(--ink-4);">
								{changed.length} change{changed.length === 1 ? '' : 's'}
							</span>
							<!-- <a
								href="/c/{company?.ticker}/changes/{ds.documentType}"
								class="meta"
								style="margin-left: auto; color: var(--teal-2);">Full report →</a
							> -->
						</div>
						{#each changed as t (t.id)}
							<DiffRow
								topic={t}
								leftFiling={ds.leftFiling}
								rightFiling={ds.rightFiling}
								{company}
							/>
						{/each}
					</div>
				{/if}
			{/each}
		</section>
	{/if}
{:else}
	<div style="text-align: center; padding: 4rem 0;">
		<p class="body-text" style="color: var(--ink-3);">No filing data available.</p>
	</div>
{/if}

<style>
	/* Document-type group: non-clickable header over its list of change rows. */
	.diff-group {
		margin-top: 2rem;
	}
	.diff-group-head {
		display: flex;
		align-items: baseline;
		gap: 12px;
		margin-bottom: 0.25rem;
	}
	.diff-group-title {
		font-family: var(--serif);
		font-size: 16px;
		color: var(--ink);
	}

	.filing-hero {
		display: grid;
		grid-template-columns: 1fr 380px;
		gap: 80px;
		align-items: start;
	}
	@media (max-width: 768px) {
		.filing-hero {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
	}

	.analysis-layout {
		display: grid;
		grid-template-columns: 220px 1fr;
		gap: 80px;
		align-items: start;
	}
	.analysis-toc {
		position: sticky;
		top: 100px;
		align-self: start;
	}
	@media (max-width: 768px) {
		.analysis-layout {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
		.analysis-toc {
			position: static;
		}
	}

	.docrow-filing {
		display: grid;
		grid-template-columns: 40px 1fr auto auto;
		gap: 1rem;
		align-items: center;
		padding: 0.875rem 1.5rem;
		border-bottom: 1px solid var(--rule);
		text-decoration: none;
		color: inherit;
		transition: background 0.1s;
	}
	.docrow-filing:last-child {
		border-bottom: none;
	}
	.docrow-filing:hover {
		background: var(--paper-2);
	}
	@media (max-width: 767.98px) {
		.docrow-filing {
			grid-template-columns: auto 1fr auto auto;
			gap: 0.5rem;
			padding: 0.875rem 1rem;
		}
		/* Let cells shrink and long type tokens wrap, never forcing overflow. */
		.docrow-filing > div {
			min-width: 0;
			overflow-wrap: anywhere;
		}
	}

	.btn-filing-primary {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 10px 16px;
		font-size: 13px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--paper);
		background: var(--ink);
		border: 1px solid var(--ink);
		border-radius: 8px;
		text-decoration: none;
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.btn-filing-primary:hover {
		opacity: 0.85;
	}
</style>
