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
<section class="py-4">
	<div class="eyebrow mb-7">
		<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;INDEPENDENT SEC FILING INTELLIGENCE
	</div>
	<h1 class="display mb-8 max-w-[14ch] pt-4">
		Read every filing.<br />
		<em>Or have it read for you.</em>
	</h1>
	<div class="mt-14 grid grid-cols-1 gap-8 md:grid-cols-2 md:gap-20">
		<p class="lede max-w-[44ch] text-ink-2">
			Every quarter, thousands of public companies file disclosures with the SEC. Symbology
			retrieves them, distills them, and surfaces what's actually changed &mdash; quarter by
			quarter, year by year, across the companies you care about.
		</p>
		<div class="flex flex-col gap-4 pt-1.5">
			<div class="flex flex-col gap-4 md:flex-row">
				<a
					href="/companies"
					class="inline-flex w-full cursor-pointer items-center justify-center rounded-lg border border-ink bg-ink px-[22px] py-3 font-sans text-sm font-medium text-paper no-underline transition-opacity duration-150 hover:opacity-85 md:w-auto"
					>Browse companies &rarr;</a
				>
				<a
					href="/faq"
					class="inline-flex w-full cursor-pointer items-center justify-center rounded-lg border border-rule-2 bg-transparent px-[22px] py-3 font-sans text-sm font-medium text-ink no-underline transition-colors duration-150 hover:border-ink-4 md:w-auto"
					>How it works</a
				>
			</div>
			<div class="meta mt-1.5 text-ink-4">
				No third-party data providers &middot; Sourced directly from SEC EDGAR
			</div>
		</div>
	</div>
</section>

<!-- Proof section -->
<section class="hairline-section">
	<div class="grid-3 pt-2">
		{#each proofCards as card (card.num)}
			<div>
				<div class="mb-[18px] font-mono text-[11px] text-ink-4">
					{card.num}
				</div>
				<div class="eyebrow mb-3">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;{card.eyebrow}
				</div>
				<h3
					class="mb-3.5 font-serif text-[26px] leading-[1.2] font-normal tracking-[-0.015em] text-ink"
				>
					{card.title}
				</h3>
				<p class="body-text text-[15px] leading-[1.6] text-ink-2">
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
	<section class="hairline-section">
		<div class="stats">
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
