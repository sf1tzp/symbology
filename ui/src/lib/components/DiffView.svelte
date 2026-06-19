<script lang="ts">
	import { formatDate, formatFilingPeriod } from '$lib/utils/filings';
	import type { CompanyResponse } from '$lib/api-types';
	import { ChevronDown, TrendingUp } from '@lucide/svelte';
	import SectionHead from './SectionHead.svelte';

	interface DiffOp {
		op: 'equal' | 'insert' | 'delete';
		text: string;
	}
	interface FilingRef {
		form: string;
		filingDate: string | null;
		periodOfReport: string | null;
		accessionNumber: string;
		/** Short content hash of this side's document, for the /d deep link. */
		documentHash: string | null;
	}
	interface Topic {
		sectionPath: string | null;
		heading: string | null;
		changeKind: string;
		ops: DiffOp[];
		truncated: boolean;
	}

	let {
		topic,
		leftFiling,
		rightFiling,
		company = null,
		showHeader = false
	}: {
		topic: Topic;
		leftFiling: FilingRef | null;
		rightFiling: FilingRef | null;
		company?: CompanyResponse | null;
		showHeader?: boolean;
	} = $props();

	// One op list reconstructs both columns: left = equal+delete, right = equal+insert.
	const leftOps = $derived(topic.ops.filter((o) => o.op === 'equal' || o.op === 'delete'));
	const rightOps = $derived(topic.ops.filter((o) => o.op === 'equal' || o.op === 'insert'));

	// On mobile, showing both the removed (left) and added (right) columns is
	// overwhelming, so we keep only the side that carries the meaningful change for
	// this change kind and collapse the other behind a toggle. Unmapped kinds keep
	// both sides. Desktop always shows both (the collapse is mobile-only CSS).
	const PRIMARY_SIDE: Record<string, 'added' | 'removed'> = {
		escalated: 'added',
		de_emphasised: 'removed',
		reworded: 'added'
	};
	const primarySide = $derived(PRIMARY_SIDE[topic.changeKind] ?? null);
	const leftSecondary = $derived(primarySide === 'added');
	const rightSecondary = $derived(primarySide === 'removed');
	const secondaryLabel = $derived(leftSecondary ? 'removed' : rightSecondary ? 'added' : null);

	let expanded = $state(false);

	// Fiscal-period label including the quarter for 10-Q (e.g. "FY 2024 Q1 10-Q"),
	// reusing the canonical formatter so quarters honour the company's fiscal year.
	const fyLabel = (f: FilingRef | null): string => {
		if (!f) return '';
		const period = formatFilingPeriod(
			{ form: f.form, period_of_report: f.periodOfReport ?? f.filingDate },
			company
		);
		return period.includes(f.form) ? period : `${period} ${f.form}`.trim();
	};
</script>

<div class="diff-block mb-8">
	{#if showHeader}
		<SectionHead sticky stickyHeading eyebrow="" heading="Side-by-side against the prior filing." />

		<div class="eyebrow" style="margin-bottom: 8px;">
			<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{(topic.changeKind || '')
				.replace('_', '-')
				.toUpperCase()}
			{#if topic.sectionPath}&nbsp;·&nbsp;{topic.sectionPath}{/if}
			<TrendingUp class="size-8" />
		</div>
		{#if topic.heading}
			<h3 class="section" style="margin-bottom: 18px;">{topic.heading}</h3>
		{/if}
	{/if}

	<div class="compare {expanded ? 'is-expanded' : ''}">
		<div class="compare-col {leftSecondary ? 'compare-col--secondary' : ''}">
			<h4>
				{#if leftFiling?.documentHash}
					<a class="diff-doc-link" href="/d/{leftFiling.accessionNumber}/{leftFiling.documentHash}"
						>{fyLabel(leftFiling)}</a
					>
				{:else}
					<span>{fyLabel(leftFiling)}</span>
				{/if}
				<div style="display: flex; gap: 28px; align-items: center; ">
					<span class="del" style="padding: 2px 8px;">Removed</span>
				</div>
				{#if leftFiling?.filingDate}
					<span class="meta" style="color: var(--ink-4);"
						>Filed {formatDate(leftFiling.filingDate)}</span
					>
				{/if}
			</h4>
			<div class="compare-text">
				{#if leftOps.length === 0}
					<p class="meta" style="color: var(--ink-4);">Not present in this filing.</p>
				{:else}
					<p>
						{#each leftOps as op, i (i)}{#if op.op === 'delete'}<span class="del">{op.text}</span
								>{:else}{op.text}{/if}{/each}
					</p>
				{/if}
			</div>
		</div>

		<div class="compare-col {rightSecondary ? 'compare-col--secondary' : ''}">
			<h4>
				{#if rightFiling?.documentHash}
					<a
						class="diff-doc-link"
						href="/d/{rightFiling.accessionNumber}/{rightFiling.documentHash}"
						>{fyLabel(rightFiling)}</a
					>
				{:else}
					<span>{fyLabel(rightFiling)}</span>
				{/if}
				<div style="display: flex; gap: 28px; align-items: center;">
					<span class="ins" style="padding: 2px 8px;">Added</span>
				</div>
				{#if rightFiling?.filingDate}
					<span class="meta" style="color: var(--ink-4);"
						>Filed {formatDate(rightFiling.filingDate)}</span
					>
				{/if}
			</h4>
			<div class="compare-text">
				{#if rightOps.length === 0}
					<p class="meta" style="color: var(--ink-4);">Not present in this filing.</p>
				{:else}
					<p>
						{#each rightOps as op, i (i)}{#if op.op === 'insert'}<span class="ins">{op.text}</span
								>{:else}{op.text}{/if}{/each}
					</p>
				{/if}
			</div>
		</div>
		{#if secondaryLabel}
			<!-- A grid item so CSS `order` can place it between the primary side and
				 the revealed secondary side on mobile; both sides always show at md+. -->
			<button
				type="button"
				class="compare-toggle md:hidden"
				aria-expanded={expanded}
				onclick={() => (expanded = !expanded)}
			>
				<ChevronDown
					class="h-3.5 w-3.5"
					style="transition: transform 0.15s; transform: rotate({expanded ? 0 : -90}deg);"
				/>
				{expanded ? `Hide ${secondaryLabel} side` : `Show ${secondaryLabel} side`}
			</button>
		{/if}
	</div>

	{#if topic.truncated}
		<p class="meta" style="color: var(--ink-4); margin-top: 10px;">Diff truncated for length.</p>
	{/if}
</div>

<style>
	/* Each column header deep-links to that side's own document page. */
	.diff-doc-link {
		color: var(--teal-2);
		text-decoration: none;
		border-bottom: 1px solid color-mix(in oklch, var(--teal-2) 35%, transparent);
		transition: border-color 0.15s;
	}
	.diff-doc-link:hover {
		border-bottom-color: var(--teal-2);
	}
</style>
