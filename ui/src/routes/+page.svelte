<script lang="ts">
	import { onMount } from 'svelte';
	import type { CompanyListItem } from '$lib/api-types';
	import { titleCase } from 'title-case';
	import { cleanContent, formatDate } from '$lib/utils/filings';
	import { ArrowRight } from '@lucide/svelte';

	interface PlatformStats {
		companies: number;
		filings: number;
		documents: number;
		earliest_year: number | null;
	}

	let stats = $state<PlatformStats | null>(null);
	let exampleCompany = $state<CompanyListItem | null>(null);
	let exampleSummary = $state<string | null>(null);

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

	function formatStatValue(n: number): string {
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
		if (n >= 1_000) return n.toLocaleString();
		return String(n);
	}

	function truncateToSentences(text: string, maxSentences: number = 3): string {
		const cleaned = cleanContent(text) ?? '';
		const sentences = cleaned.match(/[^.!?]+[.!?]+/g);
		if (!sentences) return cleaned.substring(0, 300);
		return sentences.slice(0, maxSentences).join('').trim();
	}

	onMount(async () => {
		// Fetch stats and a featured company in parallel
		const [statsRes, companiesRes] = await Promise.all([
			fetch('/api/stats'),
			fetch('/api/companies?search=adi')
		]);

		if (statsRes.ok) {
			stats = await statsRes.json();
		}

		if (companiesRes.ok) {
			const data = await companiesRes.json();
			if (data.companies?.length > 0) {
				exampleCompany = data.companies[0];

				// Fetch frontpage summary for the example company
				const summaryRes = await fetch(
					`/api/companies/${encodeURIComponent(exampleCompany.ticker)}/summary`
				);
				if (summaryRes.ok) {
					const summaryData = await summaryRes.json();
					if (summaryData.summary) {
						exampleSummary = truncateToSentences(summaryData.summary, 3);
					}
				}
			}
		}
	});
</script>

<!-- Hero -->
<section style="padding-top: 5rem; padding-bottom: 5rem;">
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

<!-- Example company -->
{#if exampleCompany}
	<section class="hairline-section" style="margin-top: 5rem;">
		<div class="flex-between" style="align-items: flex-end; margin-bottom: 28px;">
			<div>
				<div class="eyebrow" style="margin-bottom: 10px;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;A REAL EXAMPLE
				</div>
				<h2 class="section-heading">
					{titleCase((exampleCompany.display_name || exampleCompany.name).toLowerCase())}
					{#if exampleCompany.last_filing_form}
						&middot; {exampleCompany.last_filing_form}
					{/if}
				</h2>
			</div>
			<a
				href="/c/{exampleCompany.ticker}"
				class="meta"
				style="color: var(--teal-2); text-decoration: none;"
			>
				Open {exampleCompany.ticker} &rarr;
			</a>
		</div>
		<a
			href="/c/{exampleCompany.ticker}"
			style="display: block; border: 1px solid var(--rule); border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; transition: border-color 0.15s;"
			class="hover-card"
		>
			<div class="flex-between" style="padding: 20px 28px; border-bottom: 1px solid var(--rule);">
				<div style="display: flex; align-items: center; gap: 14px;">
					<span class="tag" style="font-weight: 500; color: var(--ink);">
						{exampleCompany.ticker}
					</span>
					<span style="font-family: var(--serif); font-size: 18px;">
						{titleCase((exampleCompany.display_name || exampleCompany.name).toLowerCase())}
					</span>
					{#if exampleCompany.last_filing_form && exampleCompany.last_filing_date}
						<span class="meta" style="color: var(--ink-4);">
							{exampleCompany.last_filing_form} &middot; Filed {formatDate(
								exampleCompany.last_filing_date
							)}
						</span>
					{/if}
				</div>
				{#if exampleCompany.filing_count > 0}
					<span class="meta" style="color: var(--ink-4);">
						{exampleCompany.filing_count} filings tracked
					</span>
				{/if}
			</div>
			<div class="p-8">
				{#if exampleSummary}
					<p
						style="font-family: var(--serif); font-size: 17px; line-height: 1.65; color: var(--ink-2); margin: 0;"
					>
						{exampleSummary}
					</p>
				{:else if exampleCompany.sic_description}
					<p
						style="font-family: var(--serif); font-size: 17px; line-height: 1.65; color: var(--ink-2); margin: 0;"
					>
						{exampleCompany.sic_description}
					</p>
				{/if}
				<p class="flex justify-end pt-4 font-serif text-ink-3">
					Click to view the full filing timeline, change analysis, and AI-generated insights. <ArrowRight
					/>
				</p>
			</div>
		</a>
	</section>
{/if}

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
	.hover-card:hover {
		border-color: var(--rule-2) !important;
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
	.stat .k {
		font-family: var(--mono);
		font-size: 10.5px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--ink-3);
	}
	.stat .v {
		font-family: var(--serif);
		font-size: 28px;
		font-weight: 400;
		color: var(--ink);
		letter-spacing: -0.01em;
	}
	.stat .d {
		font-family: var(--mono);
		font-size: 11.5px;
		color: var(--teal-2);
	}
	.stat .d.down {
		color: var(--danger);
	}
	.stat .d.flat {
		color: var(--ink-3);
	}
</style>
