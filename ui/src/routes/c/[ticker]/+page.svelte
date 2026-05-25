<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { ChevronLeft, ExternalLink, ChevronRight } from '@lucide/svelte';
	import SectionHead from '$lib/components/SectionHead.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import FilingTimeline from '$lib/components/filings/FilingTimeline.svelte';
	import FilingDetailPanel from '$lib/components/filings/FilingDetailPanel.svelte';
	import AggregateSummaryCard from '$lib/components/content/AggregateSummaryCard.svelte';
	import GeneratedContentTable from '$lib/components/content/GeneratedContentTable.svelte';
	import type { PageData } from './$types';
	import type { FilingTimelineResponse } from '$lib/api-types';
	import { cleanContent, formatDate, formatFilingPeriod } from '$lib/utils/filings';

	let { data }: { data: PageData } = $props();

	// All data derived reactively so client-side navigations between /c/[ticker] routes update
	const ticker = $derived(data.ticker);
	const company = $derived(data.company);
	const aggregateSummaries = $derived(data.aggregateSummaries || []);
	const filings = $derived(data.filings || []);
	const allGeneratedContent = $derived(data.allGeneratedContent || []);
	const companyGroups = $derived(data.companyGroups || []);
	const error = $derived(data.error);

	const financialComparison = $derived(data.financialComparison || null);

	let selectedFiling: FilingTimelineResponse | null = $derived(
		filings.length > 0 ? filings[filings.length - 1] : null
	);

	function handleFilingSelect(filing: FilingTimelineResponse) {
		selectedFiling = filing;
	}

	const displayCompany = $derived(
		company || {
			id: 'unknown',
			name: `${ticker} Company`,
			ticker: ticker,
			display_name: `${ticker} Company`,
			summary: 'Company information not available.',
			sic_description: 'Unknown',
			exchanges: [],
			former_names: []
		}
	);

	let backHref = $state('/companies');
	let backLabel = $state('All companies');

	afterNavigate(({ from }) => {
		if (from?.url) {
			const path = from.url.pathname;
			backHref = path + from.url.search;
			if (path === '/search') {
				backLabel = 'Search';
			} else if (path.startsWith('/groups/')) {
				const slug = path.split('/').pop() || '';
				const groupName = slug
					.split('-')
					.map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
					.join(' ');
				backLabel = groupName;
			} else if (path === '/groups') {
				backLabel = 'Groups';
			} else if (path === '/companies') {
				backLabel = 'All companies';
			}
		}
	});

	const exchangeLabel = $derived(
		displayCompany.exchanges?.length ? displayCompany.exchanges[0] : null
	);

	// Derive stats from loaded data
	const lastFiling = $derived(filings.length > 0 ? filings[filings.length - 1] : null);
	const firstFiling = $derived(filings.length > 0 ? filings[0] : null);
	const trackingSince = $derived(firstFiling ? formatFilingPeriod(firstFiling, company) : null);

	// Clean summary for the analyst brief
	const cleanedSummary = $derived(
		displayCompany.summary ? cleanContent(displayCompany.summary) : null
	);
</script>

<svelte:head>
	<title>{displayCompany.display_name || displayCompany.name} ({ticker}) - Symbology</title>
	<meta
		name="description"
		content="Financial analysis and insights for {displayCompany.display_name ||
			displayCompany.name}"
	/>
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href={backHref}
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{backLabel}
	</a>
</div>

{#if error}
	<div
		style="border-left: 3px solid var(--danger); padding: 1rem 1.25rem; margin-bottom: 2rem; background: color-mix(in oklch, var(--danger) 8%, var(--paper));"
	>
		<p class="meta" style="color: var(--danger); font-weight: 500;">Error loading company data</p>
		<p class="meta" style="margin-top: 4px; color: var(--ink-3);">{error}</p>
	</div>
{/if}

<!-- Masthead -->
<header style="display: grid; grid-template-columns: 1fr auto; gap: 2rem; align-items: end;">
	<div>
		<div class="eyebrow" style="margin-bottom: 1rem;">
			<span style="color: var(--teal-2);">&#9679;</span
			>&nbsp;&nbsp;{#if exchangeLabel}{exchangeLabel}
				&middot;{/if}
			{displayCompany.sic_description || 'Public Company'}
			{#if trackingSince}&middot; TRACKED SINCE {trackingSince}{/if}
		</div>
		<h1 class="display" style="margin-bottom: 0.75rem;">
			{displayCompany.display_name || displayCompany.name}
		</h1>
	</div>
	<div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.75rem;">
		<div style="display: flex; gap: 0.5rem;">
			<span class="tag" style="font-weight: 500; color: var(--ink);">{ticker}</span>
			<a
				href="https://finance.yahoo.com/quote/{ticker}/"
				target="_blank"
				rel="noopener noreferrer"
				class="tag flex items-center gap-1 no-underline transition-colors hover:border-rule-2"
			>
				<ExternalLink class="h-3 w-3" />
				Yahoo Finance
			</a>
		</div>
	</div>
</header>

<!-- Stats Strip -->
{#if filings.length > 0}
	<div
		class="grid-4"
		style="margin-top: 2.5rem; padding: 1.5rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);"
	>
		<div class="stat">
			<span class="stat-value">{filings.length}</span>
			<span class="stat-label">Filings Tracked</span>
		</div>
		<div class="stat">
			<span class="stat-value">{allGeneratedContent.length}</span>
			<span class="stat-label">Analyses Generated</span>
		</div>
		{#if lastFiling}
			<div class="stat">
				<span class="stat-value" style="font-size: 1.75rem;">{lastFiling.form}</span>
				<span class="stat-label">Last Filing &middot; {formatDate(lastFiling.filing_date)}</span>
			</div>
		{/if}
		{#if trackingSince}
			<div class="stat">
				<span class="stat-value" style="font-size: 1.75rem;">{trackingSince}</span>
				<span class="stat-label">Earliest Filing</span>
			</div>
		{/if}
	</div>
{/if}

<!-- Analyst Brief -->
{#if cleanedSummary}
	<section style="margin-top: 3.5rem;">
		<div class="two-col">
			<div>
				<h3 class="sub" style="margin-bottom: 14px;">The Brief</h3>
				<p class="meta" style="color: var(--ink-4); line-height: 1.6; max-width: 32ch;">
					Synthesised across
					<span style="color: var(--ink-2); font-weight: 500;">{filings.length} filings</span>
					{#if trackingSince}
						spanning {trackingSince} to present
					{/if}.
					{#if aggregateSummaries.length > 0}
						Updated
						<span style="color: var(--teal-2);">{formatDate(aggregateSummaries[0].created_at)}</span
						>.
					{/if}
				</p>
				{#if aggregateSummaries.length > 0}
					<div style="margin-top: 1.5rem;">
						<button
							class="meta"
							style="cursor: pointer; background: none; border: none; padding: 0; color: var(--teal-2);"
							onclick={() => {
								document.getElementById('change-analysis')?.scrollIntoView({ behavior: 'smooth' });
							}}
						>
							View change analysis &rarr;
						</button>
					</div>
				{/if}
			</div>
			<div class="analysis-body">
				<MarkdownContent content={cleanedSummary} />
			</div>
		</div>
	</section>
{/if}

<!-- Change Analysis Reports -->
{#if aggregateSummaries.length > 0}
	<section id="change-analysis" class="hairline-section">
		<SectionHead eyebrow="CHANGES SINCE LAST FILING" heading="What's changed in recent filings" />
		<AggregateSummaryCard summaries={aggregateSummaries} {ticker} />
	</section>
{/if}

<!-- Filing History Timeline -->
{#if filings.length > 0}
	<section class="hairline-section">
		<SectionHead eyebrow="FILING HISTORY" heading="{filings.length} filings tracked" />
		<div style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
			<FilingTimeline
				{filings}
				{company}
				selectedId={selectedFiling?.id ?? ''}
				onselect={handleFilingSelect}
			/>
		</div>

		{#if selectedFiling}
			<div style="margin-top: 2rem;">
				<FilingDetailPanel filing={selectedFiling} {company} {financialComparison} />
			</div>
		{/if}
	</section>
{:else}
	<section class="hairline-section">
		<SectionHead eyebrow="FILINGS" heading="Filing history" />
		<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
			No filings available yet for this company.
		</p>
	</section>
{/if}

<!-- Peer Group -->
{#if companyGroups.length > 0}
	{@const group = companyGroups[0]}
	<section class="hairline-section">
		<div class="two-col">
			<div>
				<div class="eyebrow" style="margin-bottom: 10px;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;COMPANY GROUP
				</div>
				<h2 class="section-heading" style="margin-bottom: 14px;">{group.name}</h2>
				{#if group.description}
					<p class="body-text" style="color: var(--ink-2);">
						{group.description}
					</p>
				{/if}
				<div style="margin-top: 1.5rem;">
					<a href="/groups/{group.slug}" class="meta no-underline" style="color: var(--teal-2);">
						Open group &rarr;
					</a>
				</div>
			</div>
			<div style="border: 1px solid var(--rule); border-radius: 8px; overflow: hidden;">
				<div
					class="flex-between"
					style="padding: 0.875rem 1.5rem; border-bottom: 1px solid var(--rule);"
				>
					<h4 class="sub" style="font-size: 12px; color: var(--ink-2);">Members</h4>
					<span class="meta" style="color: var(--ink-4);">{group.member_count} companies</span>
				</div>
				{#if group.companies && group.companies.length > 0}
					<div style="padding: 0.5rem 1.5rem;">
						{#each group.companies as member (member.id)}
							<a
								href="/c/{member.ticker}"
								class="docrow no-underline"
								style="color: inherit; {member.ticker === ticker
									? 'background: var(--sage-2); margin: 0 -1.5rem; padding-left: 1.5rem; padding-right: 1.5rem;'
									: ''}"
							>
								<div>
									<div style="font-size: 14px; font-weight: 500; color: var(--ink);">
										{member.display_name || member.name}
									</div>
									<div class="meta" style="margin-top: 2px; color: var(--ink-4);">
										{member.ticker}
										{#if member.sic_description}
											&middot; {member.sic_description}
										{/if}
									</div>
								</div>
								<div></div>
								<div>
									<ChevronRight class="h-3.5 w-3.5" style="color: var(--ink-4);" />
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</section>
{/if}

<!-- All Generated Content -->
{#if allGeneratedContent.length > 0}
	<section class="hairline-section">
		<SectionHead eyebrow="GENERATED CONTENT" heading="All analyses" />
		<GeneratedContentTable content={allGeneratedContent} {ticker} />
	</section>
{/if}
