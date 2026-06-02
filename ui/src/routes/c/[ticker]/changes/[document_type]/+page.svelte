<script lang="ts">
	import { ChevronLeft, Sparkles } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import {
		formatFilingPeriod,
		formatDate,
		getAnalysisTypeDisplay,
		shortModelName
	} from '$lib/utils/filings';
	import { toTitleCase } from '$lib/utils';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const company = $derived(data.company);
	const documentType = $derived(data.documentType);
	const changeReport = $derived(data.changeReport);
	const sourceFilings = $derived(data.sourceFilings ?? []);

	const companyName = $derived(company?.display_name || company?.name || 'Company');
	const typeDisplay = $derived(getAnalysisTypeDisplay(documentType));

	const generationDepth = $derived(
		changeReport?.report?.generationDepth ?? changeReport?.intro?.generationDepth ?? null
	);
	const modelRaw = $derived(changeReport?.report?.model ?? changeReport?.intro?.model ?? null);
	const model = $derived(modelRaw ? shortModelName(modelRaw) : null);
	const synthesisHash = $derived(
		changeReport?.report?.contentHash ?? changeReport?.intro?.contentHash ?? null
	);
	const synthesizedOn = $derived(data.createdAt);

	function spanLabel(): string {
		if (sourceFilings.length === 0) return '';
		const periods = sourceFilings
			.map((f) => f.period_of_report ?? f.filing_date)
			.filter(Boolean)
			.sort();
		const first = periods[0]?.slice(0, 4);
		const last = periods[periods.length - 1]?.slice(0, 4);
		return first && last && first !== last ? `FY${first} → FY${last}` : first ? `FY${first}` : '';
	}

	// Find this report's source document (of the same section) within a filing.
	const docFor = (f: (typeof sourceFilings)[number]) =>
		f.documents?.find((d) => d.document_type === documentType) ?? null;

	const metadataRows = $derived([
		['Section', typeDisplay],
		...(spanLabel() ? [['Periods', spanLabel()] as [string, string]] : []),
		['Filings', `${sourceFilings.length} compared`],
		...(synthesizedOn ? [['Synthesized', formatDate(synthesizedOn)] as [string, string]] : []),
		...(model ? [['Synthesis Model', model] as [string, string]] : []),
		['Synthesis Level', `L${generationDepth ?? '—'}`],
		...(synthesisHash
			? [['Synthesis Hash', synthesisHash.substring(0, 12)] as [string, string]]
			: [])
	] as [string, string][]);

	const monoFields = new Set(['Periods', 'Synthesis Model', 'Synthesis Level', 'Synthesis Hash']);
</script>

<svelte:head>
	<title>{typeDisplay} change report - {company?.ticker} - Symbology</title>
	<meta name="description" content="{typeDisplay} change analysis for {companyName}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/c/{company?.ticker}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{toTitleCase(companyName)}
	</a>
</div>

<!-- Masthead with metadata sidebar -->
<section class="change-hero">
	<div>
		<div class="eyebrow" style="margin-bottom: 1.125rem;">
			<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;CHANGE ANALYSIS &middot; {typeDisplay.toUpperCase()}
		</div>
		<h1 class="display" style="margin-bottom: 1.125rem;">
			{typeDisplay}<em>.</em>
		</h1>
		{#if changeReport?.intro?.content}
			<p class="lede" style="max-width: 62ch; color: var(--ink-2);">
				{changeReport.intro.content}
			</p>
		{/if}
		<div
			style="margin-top: 2rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;"
		>
			{#if spanLabel()}
				<span class="tag" style="font-family: var(--mono);">{spanLabel()}</span>
			{/if}
			{#if generationDepth != null}
				<span class="tag tag-new" style="gap: 4px;">
					<Sparkles class="h-2.5 w-2.5" />
					Synthesis · L{generationDepth}
				</span>
			{/if}
		</div>
	</div>

	<!-- Report metadata card -->
	<aside class="metadata-card">
		<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1.25rem;">
			Report metadata
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
	</aside>
</section>

<!-- Article with source-filing sidebar -->
<div class="change-layout">
	<aside class="change-toc">
		<h3 class="sub" style="margin-bottom: 14px;">Synthesis Sources</h3>
		<div style="display: flex; flex-direction: column; gap: 14px;">
			{#each sourceFilings as f (f.id)}
				{@const doc = docFor(f)}
				{#if doc?.short_hash}
					<a href="/d/{f.accession_number}/{doc.short_hash}" style="text-decoration: none;">
						<div style="font-size: 15px; color: var(--ink); font-family: var(--serif);">
							{f.form} &middot; {formatFilingPeriod(f, company)}
							{typeDisplay}
						</div>
						<div class="meta text-xs" style="color: var(--teal-2);">L1 Synthesis</div>
					</a>
				{:else}
					<a href="/f/{f.accession_number}" style="text-decoration: none;">
						<div style="font-size: 15px; color: var(--ink); font-family: var(--serif);">
							{f.form} &middot; {formatFilingPeriod(f, company)}
						</div>
						<div class="meta" style="color: var(--ink-4);">Filed {formatDate(f.filing_date)}</div>
					</a>
				{/if}
			{/each}
		</div>
	</aside>

	<article>
		<SectionHead
			eyebrow="SYMBOLOGY.ONLINE l{generationDepth} SYNTHESIS"
			heading="{typeDisplay} Change Report"
			synthesisHelp
		/>
		{#if changeReport?.report?.content}
			<div class="analysis-body" style="color: var(--ink-2);">
				<MarkdownContent content={changeReport.report.content} />
			</div>
		{:else}
			<p class="body-text" style="color: var(--ink-3); padding: 2rem 0;">
				No change report content available.
			</p>
		{/if}
	</article>
</div>

<footer
	style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule); color: var(--ink-4);"
>
	<span class="meta">
		Synthesised from the {typeDisplay} section across {sourceFilings.length} filing{sourceFilings.length !==
		1
			? 's'
			: ''}{#if model}
			· {model}{/if}
	</span>
</footer>

<style>
	.change-hero {
		display: grid;
		grid-template-columns: 1fr 360px;
		gap: 64px;
		align-items: start;
	}
	@media (max-width: 768px) {
		.change-hero {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
	}

	.change-layout {
		display: grid;
		grid-template-columns: 220px 1fr;
		gap: 80px;
		align-items: start;
		margin-top: 4rem;
	}
	.change-toc {
		position: sticky;
		top: 100px;
		align-self: start;
	}
	@media (max-width: 768px) {
		.change-layout {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
		.change-toc {
			position: static;
		}
	}
</style>
