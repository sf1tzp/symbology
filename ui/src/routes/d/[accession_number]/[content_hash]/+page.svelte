<script lang="ts">
	import { ChevronLeft, ExternalLink, Sparkles, ScrollText, FileText } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import * as Tabs from '$lib/components/ui/tabs';
	import {
		formatDate,
		formatFilingPeriodLong,
		getAnalysisTypeDisplay,
		shortModelName
	} from '$lib/utils/filings';
	import type { PageData } from './$types';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import { toTitleCase } from '$lib/utils';

	let { data }: { data: PageData } = $props();

	const doc = $derived(data.document);
	const filing = $derived(data.filing);
	const company = $derived(data.company);
	const shortHash = $derived(doc.short_hash || data.content_hash.substring(0, 8));
	const typeDisplay = $derived(getAnalysisTypeDisplay(doc.document_type));
	const pageContent = $derived(data.documentPageContent);
	const hasAnalysis = $derived(
		!!(pageContent && (pageContent.intro?.content || pageContent.summary?.content))
	);

	// ── Derived stats about the source document and generated analysis ──
	function wordCount(text: string | null | undefined): number {
		if (!text) return 0;
		return text.trim().split(/\s+/).filter(Boolean).length;
	}
	function formatCount(n: number): string {
		if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`;
		return String(n);
	}

	const sourceWords = $derived(wordCount(doc.content));
	const analysisWords = $derived(
		wordCount(pageContent?.summary?.content) + wordCount(pageContent?.intro?.content)
	);
	const sourceReadMinutes = $derived(Math.max(1, Math.round(sourceWords / 200)));
	const analysisReadMinutes = $derived(Math.max(1, Math.round(analysisWords / 200)));
	const generationDepth = $derived(
		pageContent?.summary?.generationDepth ?? pageContent?.intro?.generationDepth ?? null
	);
	const synthesisModelRaw = $derived(
		pageContent?.summary?.model ?? pageContent?.intro?.model ?? null
	);
	const synthesisModel = $derived(synthesisModelRaw ? shortModelName(synthesisModelRaw) : null);
	const synthesisHash = $derived(
		pageContent?.summary?.contentHash ?? pageContent?.intro?.contentHash ?? null
	);
	const synthesizedOn = $derived(pageContent?.createdAt);

	const metadataRows = $derived([
		['Section', typeDisplay],
		['Document Hash', shortHash],
		...(synthesizedOn ? [['Synthesized', formatDate(synthesizedOn)] as [string, string]] : []),
		...(synthesisModel ? [['Synthesis Model', synthesisModel] as [string, string]] : []),
		['Synthesis Level', hasAnalysis ? `L${generationDepth ?? '—'}` : 'Not generated'],
		...(synthesisHash
			? [['Synthesis Hash', synthesisHash.substring(0, 12)] as [string, string]]
			: [])
	] as [string, string][]);

	const monoFields = new Set([
		'Document Hash',
		'Synthesis Hash',
		'Synthesis Model',
		'Synthesis Level'
	]);
</script>

<svelte:head>
	<title>{typeDisplay} - {company?.ticker} - Symbology</title>
	<meta name="description" content="{typeDisplay} from {company?.ticker} SEC filing" />
</svelte:head>

<!-- Back link -->
<div class="text-md mt-4 mb-8">
	{#if filing}
		<a
			href="/f/{filing.accession_number}"
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			<FileText class="h-3 w-3" />
			{toTitleCase(company?.name ?? '')} &middot; {filing.form}
			{#if filing.period_of_report}&middot; {formatDate(filing.period_of_report)}{/if}
		</a>
	{:else}
		<a
			href="/c/{company?.ticker}"
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			{company?.ticker}
		</a>
	{/if}
</div>

<!-- SECTION 1: Hero with metadata sidebar -->
<section class="doc-hero">
	<!-- Left column -->
	<div>
		<div class="eyebrow" style="margin-bottom: 1rem;">
			<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{formatFilingPeriodLong(
				filing,
				company
			)} &middot; {typeDisplay}
		</div>
		<h1 class="display" style="margin-bottom: 1.25rem;">
			{typeDisplay}<em>.</em>
		</h1>
		{#if pageContent?.intro?.content}
			<p class="lede" style="color: var(--ink-2); max-width: 60ch; margin-bottom: 1.5rem;">
				{pageContent.intro.content}
			</p>
		{/if}
		<div
			style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;"
		>
			<span class="tag" style="font-weight: 500; color: var(--ink);">{company?.ticker}</span>
			{#if filing}
				<span class="tag">{filing.form}</span>
				<span class="tag">{formatDate(filing.filing_date)}</span>
			{/if}
			{#if hasAnalysis}
				<span class="tag tag-new" style="gap: 4px;">
					<Sparkles class="h-2.5 w-2.5" />
					Synthesis
				</span>
			{/if}
		</div>
	</div>

	<!-- Right column: Document Metadata card -->
	<aside class="metadata-card">
		<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1.25rem;">
			Document metadata
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

		<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.25rem 0;" />

		<!-- Stats -->
		<div class="meta-stats">
			<div class="meta-stat">
				<div class="meta-stat-value">{formatCount(sourceWords)}</div>
				<div class="meta-stat-label">Source words</div>
			</div>
			<div class="meta-stat">
				<div
					class="meta-stat-value"
					style="color: {hasAnalysis ? 'var(--teal-2)' : 'var(--ink-4)'};"
				>
					{hasAnalysis ? formatCount(analysisWords) : '—'}
				</div>
				<div class="meta-stat-label">Analysis words</div>
			</div>
			<div class="meta-stat">
				<div
					class="meta-stat-value"
					style="color: {hasAnalysis ? 'var(--teal-2)' : 'var(--ink-4)'}"
				>
					{hasAnalysis ? analysisReadMinutes : sourceReadMinutes}<span style="font-size: 1rem;"
						>m</span
					>
				</div>
				<div class="meta-stat-label">Est. read</div>
			</div>
		</div>

		{#if filing?.url}
			<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.25rem 0;" />
			<a href={filing.url} target="_blank" rel="noopener noreferrer" class="btn-doc-primary">
				View on SEC.gov
				<ExternalLink class="h-3.5 w-3.5" />
			</a>
		{/if}
	</aside>
</section>

<!-- Analysis + source document, tabbed -->
<section class="hairline-section">
	<Tabs.Root value={hasAnalysis ? 'analysis' : 'document'}>
		<Tabs.List class="gap-1 bg-paper-2 p-1">
			{#if hasAnalysis}
				<Tabs.Trigger
					value="analysis"
					class="cursor-pointer px-4 text-ink-3 hover:text-ink data-active:font-semibold data-active:text-teal-2"
				>
					<Sparkles class="h-3.5 w-3.5" />
					Synthesis
				</Tabs.Trigger>
			{/if}
			<Tabs.Trigger
				value="document"
				class="cursor-pointer px-4 text-ink-3 hover:text-ink data-active:font-semibold data-active:text-ink"
			>
				<ScrollText class="h-3.5 w-3.5" />
				Source Document
			</Tabs.Trigger>
		</Tabs.List>

		{#if hasAnalysis}
			<Tabs.Content value="analysis">
				<section style="margin-top: 1.5rem;">
					<SectionHead
						eyebrow="SYMBOLOGY.ONLINE l{generationDepth} SYNTHESIS"
						heading="{typeDisplay} Analysis"
						synthesisHelp
					/>
					{#if pageContent?.summary?.content}
						<div class="body-text" style="color: var(--ink-2);">
							<MarkdownContent content={pageContent.summary.content} />
						</div>
					{/if}
				</section>
			</Tabs.Content>
		{/if}

		<Tabs.Content value="document">
			<article style="margin-top: 1.5rem;">
				<SectionHead eyebrow="Source Document Text" heading="Source Document" />
				{#if doc.content}
					<div class="analysis-body">
						<MarkdownContent content={doc.content} />
					</div>
				{:else}
					<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
						No content available for this document.
					</p>
				{/if}
			</article>
		</Tabs.Content>
	</Tabs.Root>
</section>

<!-- Footer -->
{#if filing}
	<footer
		style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule); display: flex; flex-wrap: wrap; gap: 1rem; align-items: center;"
	>
		<span class="meta flex items-center gap-1.5" style="color: var(--ink-4);"> </span>
		<a
			href="/f/{filing.accession_number}"
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			<FileText class="h-3 w-3" />
			{toTitleCase(company?.name ?? '')} &middot; {filing.form}
			{#if filing.period_of_report}&middot; {formatDate(filing.period_of_report)}{/if}
		</a>
		{#if filing.url}
			<a
				href={filing.url}
				target="_blank"
				rel="noopener noreferrer"
				class="meta no-underline"
				style="color: var(--teal-2); margin-left: auto; display: inline-flex; align-items: center; gap: 4px;"
			>
				View on SEC.gov
				<ExternalLink class="w-3.t h-3.5" />
			</a>
		{/if}
	</footer>
{/if}

<style>
	.doc-hero {
		display: grid;
		grid-template-columns: 1fr 380px;
		gap: 80px;
		align-items: start;
	}
	@media (max-width: 768px) {
		.doc-hero {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
	}

	.btn-doc-primary {
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
	.btn-doc-primary:hover {
		opacity: 0.85;
	}
</style>
