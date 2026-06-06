<script lang="ts">
	import { onMount } from 'svelte';
	import { ChevronLeft, Sparkles } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import SynthesisHelp from '$lib/components/SynthesisHelp.svelte';
	import ChangeCard from '$lib/components/ChangeCard.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import DiffRow from '$lib/components/DiffRow.svelte';
	import PendingContentNotice from '$lib/components/PendingContentNotice.svelte';
	import { changeKindColor, scoreTopic, VISIBLE_KINDS } from '$lib/utils/changes';
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

	// Match the form the reader came from: plum accents + back-link on the 10-Q page.
	const selectedForm = $derived(data.selectedForm ?? '10-K');
	const accent = $derived(selectedForm === '10-Q' ? 'var(--plum)' : 'var(--teal-2)');
	const formQuery = $derived(selectedForm === '10-K' ? '' : `?form=${selectedForm}`);

	const companyName = $derived(company?.display_name || company?.name || 'Company');
	const typeDisplay = $derived(getAnalysisTypeDisplay(documentType));

	// Precomputed year-over-year structured diff. `diffSet` is the newest pairing
	// (drives the masthead + headline cards); `diffChain` is every consecutive
	// pairing oldest → newest for the multi-year side-by-side.
	const diffSet = $derived(data.diffSet);
	const diffChain = $derived(data.diffChain ?? []);
	const chainDesc = $derived([...diffChain].reverse()); // newest first for display
	const counts = $derived(diffSet?.counts ?? {});
	// On-page listings (cards + side-by-side) focus on shifts in emphasis and
	// wording of existing disclosures — new/removed topics are excluded (VISIBLE_KINDS).
	const changedTopics = $derived(
		(diffSet?.topics ?? []).filter((t) => VISIBLE_KINDS.has(t.changeKind))
	);

	type FilingRef = { form: string; filingDate: string | null; periodOfReport: string | null };
	const fyLabel = (f: FilingRef | null): string => {
		const d = f?.periodOfReport ?? f?.filingDate;
		const yr = d ? new Date(d).getFullYear() : null;
		return yr ? `FY${yr}` : (f?.form ?? '');
	};
	const pairLabel = (ds: { leftFiling: FilingRef | null; rightFiling: FilingRef | null }): string =>
		`${fyLabel(ds.leftFiling)} → ${fyLabel(ds.rightFiling)}`;

	// Deep-link support: a change card on the company page links to #diff-{id};
	// open + scroll the matching <details> when targeted.
	function openHashTarget() {
		if (typeof document === 'undefined' || !location.hash) return;
		const el = document.getElementById(location.hash.slice(1));
		if (!el) return;
		if (el instanceof HTMLDetailsElement) el.open = true;
		el.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
	onMount(openHashTarget);

	// Headline change cards: the changed topics from the most recent pairing
	// (`diffSet` = the two latest forms), ranked by analyst significance so the
	// most important surface first. Styled to mirror the company page's
	// "What's new" cards rather than the kind-grouped grid.
	const headlineCards = $derived(
		[...changedTopics].sort((a, b) => scoreTopic(b) - scoreTopic(a)).slice(0, 6)
	);

	// Masthead summary like "2 new · 1 removed · 4 escalated".
	const _countLabel = $derived(
		[
			counts.new ? `${counts.new} new` : null,
			counts.removed ? `${counts.removed} removed` : null,
			counts.escalated ? `${counts.escalated} escalated` : null,
			counts.de_emphasised ? `${counts.de_emphasised} de-emphasised` : null
		]
			.filter(Boolean)
			.join(' · ')
	);

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

<svelte:window onhashchange={openHashTarget} />

<!-- Back link -->
<div class="hidden md:block" style="margin-bottom: 3rem;">
	<a
		href="/c/{company?.ticker}{formQuery}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{toTitleCase(companyName)}
	</a>
</div>

<!-- Masthead with metadata sidebar -->
<section class="change-hero">
	<div>
		<SectionHead sticky {accent} eyebrow="symbology.online COMPARATIVE SYNTHESIS" heading="" />
		<h1 class="display" style="margin-bottom: 1.25rem;">
			{toTitleCase(companyName)}<br />
			<em>{typeDisplay} analysis.</em>
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
			<!-- {#if diffSet && counts.total_compared}
				<span class="tag">{counts.total_compared} compared</span>
			{/if} -->
			<!-- {#if countLabel}
				<span class="tag tag-new">{countLabel}</span>
			{/if} -->
			{#if generationDepth != null}
				<span class="tag tag-new" style="gap: 4px;">
					<Sparkles class="h-2.5 w-2.5" />
					L{generationDepth} Comparitive Synthesis
				</span>
			{/if}
		</div>
	</div>

	<!-- Report metadata card -->
	<aside class="metadata-card hidden md:block">
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
	<aside class="change-toc hidden md:block">
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
			sticky
			stickyHeading
			{accent}
			eyebrow="symbology.online l{generationDepth} SYNTHESIS"
			heading="{toTitleCase(companyName)} - {typeDisplay} analysis."
			synthesisHelp
		/>
		{#if changeReport?.report?.content}
			<div class="analysis-body" style="color: var(--ink-2);">
				<MarkdownContent content={changeReport.report.content} />
			</div>
		{:else}
			<PendingContentNotice label="change report" />
		{/if}
	</article>
</div>

{#if diffSet && headlineCards.length > 0}
	<section class="hairline-section" style="margin-top: 4rem;">
		<SectionHead
			sticky
			stickyHeading
			{accent}
			eyebrow="WHAT'S NEW · {pairLabel(diffSet)}"
			heading="What changed in the latest {typeDisplay}."
		/>
		<div class="change-grid">
			{#each headlineCards as t (t.id)}
				<ChangeCard
					href="#diff-{t.id}"
					onclick={(e) => openDiff(e, t.id)}
					accent={changeKindColor(t.changeKind)}
					dot={false}
					heading={t.heading}
					summary={t.summary}
				>
					{#snippet header()}
						<ChangeKindTag changeKind={t.changeKind} />
					{/snippet}
					{#snippet footerLeft()}
						{#if t.sectionPath}
							<span class="meta" style="font-family: var(--mono); color: var(--ink-4);"
								>{t.sectionPath}</span
							>
						{/if}
					{/snippet}
				</ChangeCard>
			{/each}
		</div>
	</section>
{/if}

{#if chainDesc.length > 0}
	<section class="hairline-section" style="margin-top: 3rem;">
		{#each chainDesc as ds (ds.id)}
			{@const changed = ds.topics.filter((t) => VISIBLE_KINDS.has(t.changeKind))}
			<SectionHead
				sticky
				stickyHeading
				{accent}
				diffHelp={true}
				eyebrow="{pairLabel(ds)} Text Diffs"
				heading="Side-by-side against the previous {typeDisplay}{typeDisplay.slice(-1) === 's'
					? ''
					: 's'}."
			/>
			{#if changed.length > 0}
				<div class="diff-pair">
					{#each changed as t (t.id)}
						<DiffRow topic={t} leftFiling={ds.leftFiling} rightFiling={ds.rightFiling} />
					{/each}
				</div>
			{/if}
		{/each}
	</section>
{/if}

<style>
	.change-hero {
		display: grid;
		grid-template-columns: 1fr 360px;
		gap: 64px;
		align-items: start;
	}
	/* Let grid children shrink below their content's intrinsic width so a wide
	   markdown table / long token can't stretch the column and overflow the page. */
	.change-hero > *,
	.change-layout > * {
		min-width: 0;
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
