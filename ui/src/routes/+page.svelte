<script lang="ts">
	import type { PageData } from './$types';
	import FeaturedIntroCarousel from '$lib/components/landing/FeaturedIntroCarousel.svelte';
	import DiffShowcase from '$lib/components/landing/DiffShowcase.svelte';
	import Heart from '@lucide/svelte/icons/heart';
	import { supportEnabled } from '$lib/features';

	let { data }: { data: PageData } = $props();

	interface PlatformStats {
		companies: number;
		filings: number;
		documents: number;
		earliest_year: number | null;
	}

	const _stats = $derived(data.stats as PlatformStats | null);
	const featured = $derived(data.featured);
	const featuredDiff = $derived(data.featuredDiff);

	// Brand principles — the angle that differentiates Symbology from the
	// "trusted by institutions" incumbents: editorial, independent, free.
	const principles = [
		{
			eyebrow: 'EDITORIAL',
			title: 'Written to be read.',
			body: 'Filings are written to be defensible; Symbology is written to be readable. Plain-language synthesis that stays within one click of the source document it came from.'
		},
		{
			eyebrow: 'INDEPENDENT',
			title: 'Homegrown by design.',
			body: 'No data-vendor lineage, no enterprise sales team. Symbology is an independent project, and most of its synthesis runs on consumer hardware we operate ourselves.'
		},
		{
			eyebrow: 'OPEN TO ALL',
			title: 'Free for everyone.',
			body: 'Company briefs, filing summaries, and change reports are free to read. Supporters fund the backlog and unlock extras — watchlist digests, company requests — not a paywall.'
		}
	];

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

	function _formatStatValue(n: number): string {
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
			retrieves them and synthesizes readable prose from those large bodies of source documents
			&mdash; surfacing what's actually changed, quarter by quarter, year by year, across the
			companies you care about.
		</p>
		<div class="flex flex-col gap-4 pt-1.5">
			<div class="flex flex-col gap-4 md:flex-row">
				<a
					href="/c"
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
				Sourced directly from SEC EDGAR &middot; Free to read &middot; Hundreds of top companies,
				and growing
			</div>
		</div>
	</div>
</section>

<!-- Proof section -->
<section class="hairline-section">
	<div class="grid-3 pt-2">
		{#each proofCards as card (card.num)}
			<div class="hidden md:block">
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

<!-- Featured diff: a live "what changed" specimen -->
<DiffShowcase diff={featuredDiff} />

<!-- Brand principles -->
<section class="hairline-section">
	<div class="eyebrow mb-8">
		<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;WHAT SYMBOLOGY IS
	</div>
	<div class="grid-3">
		{#each principles as p (p.eyebrow)}
			<div>
				<div class="eyebrow mb-3">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;{p.eyebrow}
				</div>
				<h3
					class="mb-3.5 font-serif text-[26px] leading-[1.2] font-normal tracking-[-0.015em] text-ink"
				>
					{p.title}
				</h3>
				<p class="body-text text-[15px] leading-[1.6] text-ink-2">
					{p.body}
				</p>
			</div>
		{/each}
	</div>
</section>

<!-- Supporter initiative -->
{#if supportEnabled}
	<section class="hairline-section">
		<div
			class="overflow-hidden rounded-2xl border border-teal-2 bg-[color-mix(in_oklab,var(--sage-2)_28%,var(--paper))] shadow-[0_0_0_1px_var(--teal-2)]"
		>
			<div class="grid grid-cols-1 gap-8 p-8 md:grid-cols-[1.4fr_1fr] md:items-center md:p-10">
				<div>
					<div class="eyebrow mb-4">
						<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;EARLY-SUPPORTER FUNDRAISER
					</div>
					<h2 class="mb-4 font-serif text-[30px] leading-[1.15] tracking-[-0.02em] text-ink">
						Support Independent, Local-LLM synthesis.
					</h2>
					<p class="body-text max-w-[52ch] text-[15.5px] leading-[1.6] text-ink-2">
						As we catch up on a backlog of existing filings, we're running a fundraiser to gauge
						interest in the project. The vast majority of synthesis runs on consumer hardware in
						house — supporting for just $1/day funds ongoing synthesis and the R&amp;D behind what's
						next.
					</p>
				</div>
				<div class="flex flex-col gap-3 md:items-end">
					<a
						href="/support"
						class="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-teal-2 bg-teal-2 px-[22px] py-3 font-mono text-sm font-medium text-white no-underline transition-all duration-150 hover:brightness-[1.06] md:w-auto"
					>
						<Heart class="h-3.5 w-3.5 fill-current" /> Support Symbology
					</a>
					<span class="font-mono text-[11.5px] text-ink-4">
						No subscription · one-time · from $1/day
					</span>
				</div>
			</div>
		</div>
	</section>
{/if}

<!-- Scale / Stats strip -->
<!-- {#if stats}
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
				<span class="stat-label">Sections Synthesised</span>
			</div>
			{#if stats.earliest_year}
				<div class="stat">
					<span class="stat-value">FY{stats.earliest_year}</span>
					<span class="stat-label">Earliest Filing</span>
				</div>
			{/if}
		</div>
	</section>
{/if} -->
