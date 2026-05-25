<script lang="ts">
	import { ChevronLeft, ChevronRight, ExternalLink, Sparkles } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import {
		formatFilingPeriodLong,
		formatFilingPeriod,
		formatDate,
		getAnalysisTypeDisplay
	} from '$lib/utils/filings';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const company = $derived(data.company);
	const filing = $derived(data.filing);
	const documents = $derived(data.documents || []);
	const otherFilings = $derived(data.otherFilings || []);

	const companyName = $derived(company?.display_name || company?.name || 'Company');
	const fiscalPeriodLong = $derived(filing ? formatFilingPeriodLong(filing, company) : '');

	function getFormLabel(form: string): string {
		if (form.includes('10-K')) return 'ANNUAL REPORT';
		if (form.includes('10-Q')) return 'QUARTERLY REPORT';
		if (form.includes('8-K')) return 'CURRENT REPORT';
		if (form.includes('DEF 14A')) return 'PROXY STATEMENT';
		return form;
	}
</script>

<svelte:head>
	<title>Filing {data.filing?.form || 'Unknown'} - {companyName} - Symbology</title>
	<meta name="description" content="SEC filing details for {companyName}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/c/{company?.ticker}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{companyName}
	</a>
</div>

{#if filing}
	<!-- SECTION 1: Hero with metadata sidebar -->
	<section class="filing-hero">
		<!-- Left column -->
		<div>
			<div class="eyebrow" style="margin-bottom: 1rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{getFormLabel(filing.form)}
				&middot; FORM {filing.form}
			</div>
			<h1 class="display" style="margin-bottom: 1.25rem;">
				{companyName},<br />
				<em>{fiscalPeriodLong}.</em>
			</h1>
			<p class="lede" style="color: var(--ink-2); max-width: 36ch;">
				{filing.form} filed with the SEC on {formatDate(
					filing.filing_date
				)}{#if filing.period_of_report}, covering the period ended {formatDate(
						filing.period_of_report
					)}{/if}.
			</p>
			<div style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
				<span class="tag" style="font-family: var(--mono);">
					Accession {filing.accession_number}
				</span>
				{#if documents.length > 0}
					<span class="tag tag-new">
						{documents.length} sections analysed
					</span>
				{/if}
			</div>
		</div>

		<!-- Right column: Metadata card -->
		<aside style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
			<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1.25rem;">
				Filing metadata
			</h4>
			<div style="display: flex; flex-direction: column; gap: 0.875rem;">
				{#each [['Form type', `${filing.form} · ${getFormLabel(filing.form).toLowerCase()}`], ['Filed', formatDate(filing.filing_date)], ...(filing.period_of_report ? [['Period of report', formatDate(filing.period_of_report)]] : []), ['Filer', companyName], ...(company?.cik ? [['CIK', company.cik]] : []), ['Documents', `${documents.length} sections`]] as [k, v] (k)}
					<div style="display: flex; justify-content: space-between; gap: 1rem;">
						<span class="meta" style="color: var(--ink-4);">{k}</span>
						<span
							class="meta"
							style="color: var(--ink-2); text-align: right; font-family: {[
								'CIK',
								'Filed',
								'Period of report'
							].includes(k)
								? 'var(--mono)'
								: 'var(--sans)'};">{v}</span
						>
					</div>
				{/each}
			</div>

			{#if filing.url}
				<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.25rem 0;" />
				<a href={filing.url} target="_blank" rel="noopener noreferrer" class="btn-filing-primary">
					View on SEC.gov
					<ExternalLink class="h-3.5 w-3.5" />
				</a>
			{/if}
		</aside>
	</section>

	<!-- SECTION 2: Documents -->
	<section class="hairline-section">
		<SectionHead
			eyebrow="DOCUMENTS"
			heading="{documents.length} section{documents.length !== 1 ? 's' : ''}, in filing order."
		/>

		{#if documents.length > 0}
			<div style="border: 1px solid var(--rule); border-radius: 8px; overflow: hidden;">
				{#each documents as doc, i (doc.id)}
					<a href="/d/{filing.accession_number}/{doc.short_hash}" class="docrow-filing">
						<div class="meta" style="color: var(--ink-3);">&sect;{i + 1}</div>
						<div>
							<div style="font-size: 14px; font-weight: 500; color: var(--ink);">
								{getAnalysisTypeDisplay(doc.document_type)}
							</div>
							<div class="meta" style="margin-top: 2px; color: var(--ink-4);">
								{doc.document_type}
							</div>
						</div>
						<div>
							<span class="tag tag-new" style="font-size: 10px; gap: 4px;">
								<Sparkles class="h-2.5 w-2.5" />
								Analysis
							</span>
						</div>
						<div>
							<ChevronRight class="h-3.5 w-3.5" style="color: var(--ink-4);" />
						</div>
					</a>
				{/each}
			</div>
		{:else}
			<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
				No documents found in this filing.
			</p>
		{/if}
	</section>

	<!-- SECTION 3: Compare with -->
	{#if otherFilings.length > 0}
		<section class="hairline-section">
			<div class="grid-2" style="align-items: start;">
				<!-- Left: description -->
				<div>
					<div class="eyebrow" style="margin-bottom: 10px;">
						<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;COMPARE WITH
					</div>
					<h2 class="section-heading" style="margin-bottom: 14px;">
						Other filings from {companyName}.
					</h2>
					<p class="body-text" style="color: var(--ink-2);">
						Browse other SEC filings from {companyName} to compare disclosures, track language changes,
						and follow the company's reporting history.
					</p>
					<div style="margin-top: 1.5rem;">
						<a href="/c/{company?.ticker}" class="meta no-underline" style="color: var(--teal-2);">
							View all filings &rarr;
						</a>
					</div>
				</div>

				<!-- Right: other filings card -->
				<div style="border: 1px solid var(--rule); border-radius: 8px; overflow: hidden;">
					<div
						class="flex-between"
						style="padding: 0.875rem 1.5rem; border-bottom: 1px solid var(--rule);"
					>
						<h4 class="sub" style="font-size: 12px; color: var(--ink-2);">Other filings</h4>
						<span class="meta" style="color: var(--ink-4);">
							{otherFilings.length} filing{otherFilings.length !== 1 ? 's' : ''}
						</span>
					</div>
					<div style="padding: 0.5rem 1.5rem;">
						{#each otherFilings as other (other.id)}
							<a
								href="/f/{other.accession_number}"
								class="docrow no-underline"
								style="color: inherit;"
							>
								<div>
									<div style="font-size: 14px; font-weight: 500; color: var(--ink);">
										{other.form} &middot; {formatFilingPeriod(other, company)}
									</div>
									<div class="meta" style="margin-top: 2px; color: var(--ink-4);">
										Filed {formatDate(other.filing_date)}
									</div>
								</div>
								<div></div>
								<div>
									<ChevronRight class="h-3.5 w-3.5" style="color: var(--ink-4);" />
								</div>
							</a>
						{/each}
					</div>
				</div>
			</div>
		</section>
	{/if}
{:else}
	<div style="text-align: center; padding: 4rem 0;">
		<p class="body-text" style="color: var(--ink-3);">No filing data available.</p>
	</div>
{/if}

<style>
	.filing-hero {
		display: grid;
		grid-template-columns: 1fr 380px;
		gap: 80px;
		align-items: start;
	}
	@media (max-width: 768px) {
		.filing-hero {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
	}

	.docrow-filing {
		display: grid;
		grid-template-columns: 40px 1fr auto auto;
		gap: 1rem;
		align-items: center;
		padding: 0.875rem 1.5rem;
		border-bottom: 1px solid var(--rule);
		text-decoration: none;
		color: inherit;
		transition: background 0.1s;
	}
	.docrow-filing:last-child {
		border-bottom: none;
	}
	.docrow-filing:hover {
		background: var(--paper-2);
	}

	.btn-filing-primary {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 10px 16px;
		font-size: 13px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--paper);
		background: var(--ink);
		border: 1px solid var(--ink);
		border-radius: 8px;
		text-decoration: none;
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.btn-filing-primary:hover {
		opacity: 0.85;
	}
</style>
