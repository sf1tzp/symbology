<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';

	// Event dispatcher for parent components
	const dispatch = createEventDispatcher<{
		aggregateSelected: AggregateResponse;
		filingSelected: FilingResponse;
	}>();

	// Mock types for now - will be replaced with real API types
	interface CompanyResponse {
		id: string;
		name: string;
		display_name?: string;
		tickers: string[];
		sector?: string;
		summary?: string;
		description?: string;
	}

	interface AggregateResponse {
		id: string;
		document_type: string;
		sha: string;
		title?: string;
	}

	interface FilingResponse {
		id: string;
		filing_type: string;
		filing_date: string;
		period_of_report: string;
		edgar_id: string;
	}

	// Props
	interface Props {
		company: CompanyResponse;
		aggregates?: AggregateResponse[];
		filings?: FilingResponse[];
		loading?: boolean;
		error?: string | null;
	}

	let { company, aggregates = [], filings = [], loading = false, error = null }: Props = $props();

	// Component state
	let showFullSummary = $state(false);
	let filingsExpanded = $state(false);

	// Helper functions
	function formatTitleCase(text: string): string {
		return text
			.toLowerCase()
			.split(' ')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function formatDocumentType(type: string): string {
		return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	}

	function getFilingTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			'10-K': 'Annual Report',
			'10-Q': 'Quarterly Report',
			'8-K': 'Current Report',
			'DEF 14A': 'Proxy Statement',
			'13F': 'Holdings Report'
		};
		return labels[type] || type;
	}

	function formatYear(dateString: string): string {
		try {
			return new Date(dateString).getFullYear().toString();
		} catch {
			return dateString;
		}
	}

	function cleanContent(content?: string): string {
		if (!content) return '';
		return content.trim().replace(/\n\s*\n/g, '\n\n');
	}

	// Event handlers
	function handleAggregateClick(aggregate: AggregateResponse) {
		dispatch('aggregateSelected', aggregate);
	}

	function handleFilingClick(filing: FilingResponse) {
		dispatch('filingSelected', filing);
	}

	function toggleSummary() {
		showFullSummary = !showFullSummary;
	}

	function toggleFilings() {
		filingsExpanded = !filingsExpanded;
	}

	// Computed values
	const displayName = $derived(company.display_name || company.name);
	const cleanSummary = $derived(cleanContent(company.summary || company.description));
	const truncatedSummary = $derived(
		cleanSummary.length > 300 ? cleanSummary.substring(0, 300) + '...' : cleanSummary
	);
</script>

<div class="space-y-6">
	<!-- Company Header -->
	<Card>
		<CardHeader>
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<CardTitle class="text-2xl font-bold">
						{formatTitleCase(displayName)}
					</CardTitle>
					<div class="mt-2 flex items-center space-x-2">
						{#each company.tickers as ticker}
							<span
								class="rounded-full bg-primary px-2 py-1 text-sm font-medium text-primary-foreground"
							>
								{ticker}
							</span>
						{/each}
						{#if company.sector}
							<span class="rounded-full bg-secondary px-2 py-1 text-sm text-secondary-foreground">
								{company.sector}
							</span>
						{/if}
					</div>
				</div>
			</div>
		</CardHeader>

		{#if cleanSummary}
			<CardContent>
				<div class="prose prose-sm max-w-none">
					<p class="leading-relaxed text-muted-foreground">
						{showFullSummary ? cleanSummary : truncatedSummary}
					</p>
					{#if cleanSummary.length > 300}
						<Button variant="link" size="sm" onclick={toggleSummary} class="mt-2 h-auto p-0">
							{showFullSummary ? 'Show less' : 'Show more'}
						</Button>
					{/if}
				</div>
			</CardContent>
		{/if}
	</Card>

	<!-- Analysis Section -->
	{#if loading}
		<Card>
			<CardContent class="flex items-center justify-center py-8">
				<div class="space-y-2 text-center">
					<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-primary"></div>
					<p class="text-sm text-muted-foreground">Loading analysis...</p>
				</div>
			</CardContent>
		</Card>
	{:else if error}
		<Card>
			<CardContent class="py-8">
				<div class="space-y-4 text-center">
					<p class="text-destructive">Error loading analysis: {error}</p>
					<Button onclick={() => window.location.reload()}>Retry</Button>
				</div>
			</CardContent>
		</Card>
	{:else if aggregates.length > 0}
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Available Analysis</CardTitle>
				<CardDescription>Click to view LLM-generated analysis and insights</CardDescription>
			</CardHeader>
			<CardContent>
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each aggregates as aggregate}
						<Button
							variant="outline"
							onclick={() => handleAggregateClick(aggregate)}
							class="h-auto justify-start p-4 text-left"
						>
							<div>
								<div class="font-medium">
									{formatDocumentType(aggregate.document_type)}
								</div>
								{#if aggregate.title}
									<div class="mt-1 text-sm text-muted-foreground">
										{aggregate.title}
									</div>
								{/if}
							</div>
						</Button>
					{/each}
				</div>
			</CardContent>
		</Card>
	{/if}

	<!-- SEC Filings Section -->
	{#if filings.length > 0}
		<Card>
			<CardHeader>
				<div class="flex items-center justify-between">
					<div>
						<CardTitle class="text-lg">SEC Filings</CardTitle>
						<CardDescription>Recent regulatory filings and documents</CardDescription>
					</div>
					<Button
						variant="ghost"
						size="sm"
						onclick={toggleFilings}
						class="flex items-center space-x-1"
					>
						<span>{filingsExpanded ? 'Hide' : 'Show'} Details</span>
						<span class="transform transition-transform {filingsExpanded ? 'rotate-180' : ''}">
							▼
						</span>
					</Button>
				</div>
			</CardHeader>

			{#if filingsExpanded}
				<CardContent>
					<div class="space-y-2">
						{#each filings.slice(0, 10) as filing}
							<Button
								variant="ghost"
								onclick={() => handleFilingClick(filing)}
								class="h-auto w-full justify-between p-4"
							>
								<div class="text-left">
									<div class="font-medium">
										{formatYear(filing.period_of_report)}
										{filing.filing_type}
									</div>
									<div class="text-sm text-muted-foreground">
										{getFilingTypeLabel(filing.filing_type)}
									</div>
								</div>
								<div class="text-right text-sm text-muted-foreground">
									{new Date(filing.filing_date).toLocaleDateString()}
								</div>
							</Button>
						{/each}

						{#if filings.length > 10}
							<p class="pt-2 text-center text-sm text-muted-foreground">
								and {filings.length - 10} more filings...
							</p>
						{/if}
					</div>
				</CardContent>
			{:else}
				<CardContent>
					<p class="text-sm text-muted-foreground">
						{filings.length} filing{filings.length === 1 ? '' : 's'} available. Click "Show Details"
						to view them.
					</p>
				</CardContent>
			{/if}
		</Card>
	{/if}

	<!-- No Data States -->
	{#if !loading && !error && aggregates.length === 0 && filings.length === 0}
		<Card>
			<CardContent class="py-8">
				<div class="space-y-4 text-center">
					<div class="text-4xl">📊</div>
					<div>
						<h3 class="text-lg font-medium">No Analysis Available</h3>
						<p class="text-muted-foreground">
							Analysis and filings for this company are not yet available.
						</p>
					</div>
				</div>
			</CardContent>
		</Card>
	{/if}
</div>
