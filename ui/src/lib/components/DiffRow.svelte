<script lang="ts">
	import DiffView from './DiffView.svelte';
	import ChangeKindTag from './ChangeKindTag.svelte';
	import type { CompanyResponse } from '$lib/api-types';

	interface DiffOp {
		op: 'equal' | 'insert' | 'delete';
		text: string;
	}
	interface FilingRef {
		form: string;
		filingDate: string | null;
		periodOfReport: string | null;
		accessionNumber: string;
		documentHash: string | null;
	}
	interface Topic {
		id: string;
		sectionPath: string | null;
		heading: string | null;
		changeKind: string;
		ops: DiffOp[];
		truncated: boolean;
		summary: string | null;
	}

	// One collapsible side-by-side diff: a kind-tag (coloured to match the change cards)
	// + section title in the summary, revealing the DiffView when opened. Shared by the
	// filing page and the per-section change report.
	let {
		topic,
		leftFiling,
		rightFiling,
		company = null
	}: {
		topic: Topic;
		leftFiling: FilingRef | null;
		rightFiling: FilingRef | null;
		company?: CompanyResponse | null;
	} = $props();
</script>

<details id="diff-{topic.id}" class="diff-details">
	<summary>
		<ChangeKindTag changeKind={topic.changeKind} />
		<span class="diff-summary-body">
			<span class="diff-summary-title">{topic.heading ?? topic.sectionPath ?? 'Section'}</span>
			{#if topic.summary}
				<span class="diff-summary-text">{topic.summary}</span>
			{/if}
		</span>
		<svg
			class="diff-chevron"
			width="16"
			height="16"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<polyline points="9 6 15 12 9 18" />
		</svg>
	</summary>
	<DiffView {topic} {leftFiling} {rightFiling} {company} />
</details>

<style>
	.diff-details {
		border-top: 1px solid var(--rule);
		padding: 0.25rem 0;
		/* Deep links (openDiff) scroll a diff into view. On mobile the Compare
		   SectionHead pins, so clear its measured height (--md-heading-sticky-top,
		   published by SectionHead); on desktop it's unset and we fall back to the
		   fixed-navbar offset. */
		scroll-margin-top: var(--md-heading-sticky-top, 80px);
	}
	.diff-details > summary {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0.75rem 0;
		list-style: none;
	}
	.diff-details > summary::-webkit-details-marker {
		display: none;
	}
	/* Title + optional summary preview, stacked. Takes the row's free space and
	   wraps rather than overflowing: some section paths / run-on headings are very
	   long and would otherwise push past the viewport on mobile. min-width:0 lets
	   the flex item shrink below its content width so overflow-wrap can break it. */
	.diff-summary-body {
		display: flex;
		flex-direction: column;
		gap: 3px;
		flex: 1 1 auto;
		min-width: 0;
	}
	.diff-summary-title {
		font-family: var(--serif);
		font-size: 15px;
		color: var(--ink);
		overflow-wrap: anywhere;
	}
	/* One-line gist of the change (the same summary shown on the cards), so the row
	   is readable without expanding. */
	.diff-summary-text {
		font-size: 13px;
		line-height: 1.45;
		color: var(--ink-3);
		overflow-wrap: anywhere;
	}
	.diff-chevron {
		margin-left: auto;
		flex-shrink: 0;
		color: var(--ink-4);
		transition: transform 0.2s ease;
	}
	.diff-details[open] > summary .diff-chevron {
		transform: rotate(90deg);
	}
	.diff-details[open] > summary {
		margin-bottom: 1rem;
	}
</style>
