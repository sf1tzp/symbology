<script lang="ts">
	import type { PageData } from './$types';
	import FeaturedIntroCarousel from '$lib/components/landing/FeaturedIntroCarousel.svelte';

	let { data }: { data: PageData } = $props();

	interface PlatformStats {
		companies: number;
		filings: number;
		documents: number;
		earliest_year: number | null;
	}

	const stats = $derived(data.stats as PlatformStats | null);
	const featured = $derived(data.featured);

	const proofCards = [
		{
			num: '01',
			eyebrow: 'RETRIEVE',
			title: 'Public filings, primary source',
			body: 'Form 10-K, 10-Q, 8-K, DEF 14A and more, pulled directly from SEC EDGAR. No re-publishing or re-interpretation.'
		},
		{
			num: '02',
			eyebrow: 'DISTILL',
			title: 'Section-by-section',
			body: 'Each filing is broken into its component sections — Risk Factors, MD&A, Business Description — and distilled into a consistent, readable format.'
		},
		{
			num: '03',
			eyebrow: 'COMPARE',
			title: 'Multi-level Synthesis',
			body: 'By indexing the same sections across years and quarters, Symbology surfaces meaningful disclosure changes — automatically, with citations back to source.'
		}
	];

	function formatStatValue(n: number): string {
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
		if (n >= 1_000) return n.toLocaleString();
		return String(n);
	}
</script>

<!-- Hero -->
<section style="padding-top: 2rem; padding-bottom: 2rem;">
	<div class="eyebrow" style="margin-bottom: 28px;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;SYMBOLOGY.ONLINE &middot;
		INDEPENDENT SEC FILING INTELLIGENCE
	</div>
	<h1 class="display" style="max-width: 14ch; margin-bottom: 2rem;">
		Read every filing.<br />
		<em>Or have it read for you.</em>
	</h1>
	<div class="grid-2" style="gap: 5rem; margin-top: 3.5rem;">
		<p class="lede" style="max-width: 44ch; color: var(--ink-2);">
			Every quarter, thousands of public companies file disclosures with the SEC. Symbology
			retrieves them, distills them, and surfaces what's actually changed &mdash; quarter by
			quarter, year by year, across the companies you care about.
		</p>
		<div style="display: flex; flex-direction: column; gap: 18px; padding-top: 6px;">
			<div style="display: flex; gap: 12px;">
				<a href="/companies" class="btn-primary">Browse companies &rarr;</a>
				<a href="/faq" class="btn-secondary">How it works</a>
			</div>
			<div class="meta" style="margin-top: 6px; color: var(--ink-4);">
				No third-party data providers &middot; Sourced directly from SEC EDGAR
			</div>
		</div>
	</div>
</section>

<!-- Proof section -->
<section class="hairline-section">
	<div class="grid-3" style="padding-top: 8px;">
		{#each proofCards as card (card.num)}
			<div>
				<div
					style="font-family: var(--mono); font-size: 11px; color: var(--ink-4); margin-bottom: 18px;"
				>
					{card.num}
				</div>
				<div class="eyebrow" style="margin-bottom: 12px;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{card.eyebrow}
				</div>
				<h3
					style="font-family: var(--serif); font-weight: 400; font-size: 26px;
						       letter-spacing: -0.015em; line-height: 1.2; color: var(--ink); margin: 0 0 14px;"
				>
					{card.title}
				</h3>
				<p class="body-text" style="font-size: 15px; line-height: 1.6; color: var(--ink-2);">
					{card.body}
				</p>
			</div>
		{/each}
	</div>
</section>

<!-- Featured company intros -->
<FeaturedIntroCarousel companies={featured} />

<!-- Scale / Stats strip -->
{#if stats}
	<section class="hairline-section" style="margin-top: 5rem;">
		<div class="grid-4 stats">
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.companies)}</span>
				<span class="stat-label">Public Companies Indexed</span>
			</div>
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.filings)}</span>
				<span class="stat-label">Filings Parsed</span>
			</div>
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.documents)}</span>
				<span class="stat-label">Sections Analysed</span>
			</div>
			{#if stats.earliest_year}
				<div class="stat">
					<span class="stat-value">FY{stats.earliest_year}</span>
					<span class="stat-label">Earliest Filing</span>
				</div>
			{/if}
		</div>
	</section>
{/if}

<style>
	.btn-primary {
		display: inline-flex;
		align-items: center;
		padding: 12px 22px;
		font-size: 14px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--paper);
		background: var(--ink);
		border: 1px solid var(--ink);
		border-radius: 8px;
		cursor: pointer;
		text-decoration: none;
		transition: opacity 0.15s;
	}
	.btn-primary:hover {
		opacity: 0.85;
	}
	.btn-secondary {
		display: inline-flex;
		align-items: center;
		padding: 12px 22px;
		font-size: 14px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--ink);
		background: transparent;
		border: 1px solid var(--rule-2);
		border-radius: 8px;
		text-decoration: none;
		cursor: pointer;
		transition: border-color 0.15s;
	}
	.btn-secondary:hover {
		border-color: var(--ink-4);
	}

	/* ---------- Quick stats row ---------- */
	.stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0;
		border-top: 1px solid var(--rule);
		border-bottom: 1px solid var(--rule);
	}
	.stat {
		padding: 20px 24px;
		border-right: 1px solid var(--rule);
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.stat:last-child {
		border-right: 0;
	}
</style>
