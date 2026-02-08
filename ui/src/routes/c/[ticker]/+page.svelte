<script lang="ts">
	import { goto } from '$app/navigation';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import {
		Collapsible,
		CollapsibleTrigger,
		CollapsibleContent
	} from '$lib/components/ui/collapsible';
	import { ChevronDown, ExternalLink } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import FilingTimeline from '$lib/components/filings/FilingTimeline.svelte';
	import FilingDetailPanel from '$lib/components/filings/FilingDetailPanel.svelte';
	import AggregateSummaryCard from '$lib/components/content/AggregateSummaryCard.svelte';
	import type { PageData } from './$types';
	import type { FilingTimelineResponse } from '$lib/api-types';
	import { cleanContent } from '$lib/utils/filings';

	let { data }: { data: PageData } = $props();

	const ticker = data.ticker;
	const company = data.company;
	const aggregateSummaries = data.aggregateSummaries || [];
	const filings = data.filings || [];
	const error = data.error;

	let financialComparison = $state(data.financialComparison || null);
	let descriptionOpen = $state(false);

	// Selected filing state — default to most recent (last in ASC-sorted array)
	let selectedFiling = $state<FilingTimelineResponse | null>(
		filings.length > 0 ? filings[filings.length - 1] : null
	);

	function handleFilingSelect(filing: FilingTimelineResponse) {
		selectedFiling = filing;
	}

	const displayCompany = company || {
		id: 'unknown',
		name: `${ticker} Company`,
		ticker: ticker,
		display_name: `${ticker} Company`,
		summary: 'Company information not available.',
		sic_description: 'Unknown',
		exchanges: [],
		former_names: []
	};
</script>

<svelte:head>
	<title>{displayCompany.display_name || displayCompany.name} ({ticker}) - Symbology</title>
	<meta
		name="description"
		content="Financial analysis and insights for {displayCompany.display_name ||
			displayCompany.name}"
	/>
</svelte:head>

<div class="space-y-6">
	<!-- Header with back navigation and company info -->
	<div class="space-y-3">
		<Button variant="ghost" size="sm" onclick={() => goto('/')}>← Back to Search</Button>

		{#if error}
			<div class="rounded-md bg-red-50 p-4 text-red-700">
				<p class="font-medium">Error loading company data:</p>
				<p class="text-sm">{error}</p>
			</div>
		{/if}

		<div class="flex items-center justify-between gap-4">
			<div>
				<div class="flex items-center gap-3">
					<h1 class="text-3xl font-bold">
						{displayCompany.display_name || displayCompany.name}
					</h1>
					<span
						class="rounded-full bg-primary px-3 py-1 text-sm font-medium text-primary-foreground"
					>
						{ticker}
					</span>
				</div>
				{#if displayCompany.sic_description}
					<p class="mt-1 text-sm text-muted-foreground">{displayCompany.sic_description}</p>
				{/if}
			</div>
			<Button
				size="sm"
				variant="outline"
				href="https://finance.yahoo.com/quote/{ticker}/"
				target="_blank"
			>
				<ExternalLink class="mr-2 h-4 w-4" />
				Yahoo Finance
			</Button>
		</div>
	</div>

	<!-- Collapsible Company Description -->
	{#if displayCompany.summary && displayCompany.summary.trim()}
		<Collapsible bind:open={descriptionOpen}>
			<Card>
				<CollapsibleTrigger class="flex w-full items-center justify-between px-6 py-4 text-left">
					<span class="text-sm font-semibold">Company Description</span>
					<ChevronDown
						class="h-4 w-4 text-muted-foreground transition-transform {descriptionOpen
							? 'rotate-180'
							: ''}"
					/>
				</CollapsibleTrigger>
				<CollapsibleContent>
					<CardContent class="pt-0">
						<MarkdownContent content={cleanContent(displayCompany.summary) || ''} />
					</CardContent>
				</CollapsibleContent>
			</Card>
		</Collapsible>
	{/if}

	<!-- Aggregate Change Analysis Reports -->
	<AggregateSummaryCard summaries={aggregateSummaries} {ticker} />

	<!-- Filing History Timeline -->
	{#if filings.length > 0}
		<Card>
			<CardHeader>
				<CardTitle class="text-base">Filing History</CardTitle>
			</CardHeader>
			<CardContent>
				<FilingTimeline
					{filings}
					{company}
					selectedId={selectedFiling?.id ?? ''}
					onselect={handleFilingSelect}
				/>
			</CardContent>
		</Card>

		<!-- Selected Filing Detail Panel -->
		{#if selectedFiling}
			<FilingDetailPanel filing={selectedFiling} {company} {financialComparison} />
		{/if}
	{:else}
		<Card>
			<CardContent>
				<div class="py-8 text-center">
					<p class="text-muted-foreground">No filings available yet for this company.</p>
				</div>
			</CardContent>
		</Card>
	{/if}
</div>
