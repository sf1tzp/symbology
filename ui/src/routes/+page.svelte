<script lang="ts">
	import SectionHead from '$lib/components/SectionHead.svelte';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';

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
			title: 'Section-by-section synthesis',
			body: 'Each filing is broken into its component sections — Risk Factors, MD&A, Business Description — and distilled into a consistent, readable format.'
		},
		{
			num: '03',
			eyebrow: 'COMPARE',
			title: 'What actually changed',
			body: 'By indexing the same sections across years and quarters, Symbology surfaces meaningful disclosure changes — automatically, with citations back to source.'
		}
	];

	function scrollToExplore() {
		document.getElementById('explore')?.scrollIntoView({ behavior: 'smooth' });
	}
</script>

<!-- Hero -->
<section class="page" style="padding-top: 5rem; padding-bottom: 5rem;">
	<div class="eyebrow" style="margin-bottom: 28px;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;SYMBOLOGY &middot; INDEPENDENT SEC
		FILING INTELLIGENCE
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
				<button class="btn-primary" onclick={scrollToExplore}>Browse companies &rarr;</button>
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
	<div class="page">
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
	</div>
</section>

<!-- Explore section -->
<section id="explore" class="hairline-section" style="padding-bottom: 5rem;">
	<div class="page">
		<SectionHead eyebrow="EXPLORE" heading="Start with a company" />
		<div style="margin-top: 2rem;">
			<CompanySelector showCompanyList={true} />
		</div>
	</div>
</section>

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
</style>
