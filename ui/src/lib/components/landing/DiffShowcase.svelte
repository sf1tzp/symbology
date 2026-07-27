<script lang="ts">
	import type { CompanyResponse, LandingDiffShowcase } from '$lib/api-types';
	import DiffView from '$lib/components/DiffView.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import { getAnalysisTypeDisplay } from '$lib/utils/filings';
	import { docColor } from '$lib/utils/changes';
	import { titleCase } from 'title-case';

	let { diff }: { diff: LandingDiffShowcase | null } = $props();

	const displayName = $derived(
		diff ? titleCase((diff.display_name || diff.name).toLowerCase()) : ''
	);
	// DiffView only reads fiscal_year_end off the company (for fiscal-period labels).
	const companyForPeriods = $derived(
		diff ? ({ fiscal_year_end: diff.fiscal_year_end } as CompanyResponse) : null
	);
	const reportHref = $derived(
		diff ? `/c/${diff.ticker}/changes/${diff.documentType}#diff-${diff.sectionDiffId}` : ''
	);
</script>

{#if diff}
	<section class="hairline-section">
		<div class="mb-10 grid grid-cols-1 gap-6 md:grid-cols-[1.4fr_1fr] md:items-end">
			<div>
				<div class="eyebrow mb-2.5">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;CHANGE DETECTION
				</div>
				<h2 class="section-heading">
					See <em class="font-light text-ink-3">exactly</em> what changed.
				</h2>
			</div>
			<p
				class="body-text m-0 max-w-[46ch] text-[15px] leading-[1.6] text-ink-2 md:justify-self-end"
			>
				Filings are living documents — risk language sharpens, hedges appear, emphasis moves.
				Symbology diffs each section against the prior filing, word by word, so the edit itself
				becomes the insight.
			</p>
		</div>

		<div class="overflow-hidden rounded-lg border border-rule">
			<div
				class="flex-between flex-wrap gap-x-4 gap-y-2 border-b border-rule px-5 py-4 md:px-7 md:py-5"
			>
				<div class="flex flex-wrap items-baseline gap-3">
					<a href="/c/{diff.ticker}" class="font-serif text-xl text-ink no-underline">
						{displayName}
					</a>
					<span class="tag font-medium text-ink">{diff.ticker}</span>
				</div>
				<div class="flex flex-wrap items-center gap-3">
					<span class="meta text-xs" style="color: {docColor(diff.documentType)};">
						&#9679;&nbsp;&nbsp;{getAnalysisTypeDisplay(diff.documentType)}
					</span>
					<ChangeKindTag changeKind={diff.changeKind} />
				</div>
			</div>

			<div class="p-5 pb-2 md:p-8 md:pb-3">
				{#if diff.heading}
					<h3
						class="mt-0 mb-1.5 font-serif text-[22px] leading-[1.25] tracking-[-0.015em] text-ink"
					>
						{diff.heading}
					</h3>
				{/if}
				{#if diff.sectionPath}
					<div class="meta mb-4 text-xs text-ink-4">{diff.sectionPath}</div>
				{/if}
				{#if diff.summary}
					<p
						class="mt-0 mb-7 max-w-[68ch] border-l-2 border-teal-2 pl-4 font-serif text-[16.5px] leading-[1.6] text-ink-2"
					>
						{diff.summary}
					</p>
				{:else}
					<div class="mb-6"></div>
				{/if}

				<DiffView
					topic={{
						sectionPath: diff.sectionPath,
						heading: diff.heading,
						changeKind: diff.changeKind,
						ops: diff.ops,
						truncated: diff.truncated
					}}
					leftFiling={diff.leftFiling}
					rightFiling={diff.rightFiling}
					company={companyForPeriods}
				/>
			</div>

			<div
				class="flex-between flex-wrap gap-x-4 gap-y-2 border-t border-rule bg-paper-2 px-5 py-4 md:px-7"
			>
				<span class="meta text-xs text-ink-4">
					One of thousands of tracked section changes &middot; a new example every visit
				</span>
				<a href={reportHref} class="meta text-sm whitespace-nowrap text-teal-2 no-underline">
					Open the full {diff.ticker} change report &rarr;
				</a>
			</div>
		</div>
	</section>
{/if}
