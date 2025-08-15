<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { ExternalLink } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import type { PageData } from './$types';
	import type {
		CompanyResponse,
		GeneratedContentResponse,
		FilingResponse
	} from '$lib/generated-api-types';
	import Badge from '$lib/components/ui/badge/badge.svelte';

	let { data }: { data: PageData } = $props();

	// Extract data from loader
	const ticker = data.ticker;
	const company = data.company;
	const generatedContent = data.generatedContent || [];
	const filings = data.filings || [];
	const error = data.error;

	// Handle missing company data
	const displayCompany = company || {
		id: 'unknown',
		name: `${ticker} Company`,
		tickers: [ticker],
		display_name: `${ticker} Company`,
		summary: 'Company information not available.',
		sic_description: 'Unknown',
		exchanges: [],
		entity_type: 'Company'
	};

	// Navigation functions
	function handleBackToSearch() {
		goto('/');
	}

	function handleAnalysisClick(contentId: string, shortHash?: string) {
		// Use the short_hash if available, otherwise fall back to content ID substring
		const hash = shortHash || contentId.substring(0, 12);
		goto(`/g/${ticker}/${hash}`);
	}

	function handleFilingClick(accessionNumber: string) {
		goto(`/f/${accessionNumber}`);
	}

	function handleBrowseAnalysis() {
		goto('/analysis');
	}

	function handleBrowseFilings() {
		goto('/filings');
	}

	// Helper function to format dates
	function formatDate(dateString: string): string {
		try {
			return new Date(dateString).toLocaleDateString();
		} catch {
			return dateString;
		}
	}

	// Helper function to get analysis type display name
	function getAnalysisTypeDisplay(documentType: string): string {
		switch (documentType?.toUpperCase()) {
			case 'MANAGEMENT_DISCUSSION':
				return 'Management Discussion';
			case 'RISK_FACTORS':
				return 'Risk Factors';
			case 'BUSINESS_DESCRIPTION':
				return 'Business Description';
			default:
				return documentType;
		}
	}

	function handleBrowseAllAnalysis() {
		goto('/analysis');
	}

	function handleBrowseAllFilings() {
		goto('/filings');
	}

	function format_filing_in_list(filing: FilingResponse) {
		const year = new Date(filing.period_of_report).getFullYear();
		return `${year} ${filing.filing_type}`;
	}

	/**
	 * Clean content by removing <think> tags and internal reasoning patterns
	 */
	export function cleanContent(content: string | undefined): string | undefined {
		if (!content) return undefined;

		// Remove <think>...</think> blocks and any content before them
		let cleaned = content.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

		// Also handle cases where there might be thinking content without tags
		cleaned = cleaned.replace(
			/^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
			''
		);

		// Trim any remaining whitespace
		cleaned = cleaned.trim();

		return cleaned || undefined;
	}
</script>

<svelte:head>
	<title>{displayCompany.display_name || displayCompany.name} ({ticker}) - Symbology</title>
	<meta
		name="description"
		content="Financial analysis and insights for {displayCompany.display_name ||
			displayCompany.name}"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Header with back navigation and company info -->
	<div class="space-y-4">
		<Button variant="ghost" onclick={handleBackToSearch}>← Back to Search</Button>

		{#if error}
			<div class="rounded-md bg-red-50 p-4 text-red-700">
				<p class="font-medium">Error loading company data:</p>
				<p class="text-sm">{error}</p>
			</div>
		{/if}

		<div class="space-y-2">
			<div class="flex items-center space-x-3">
				<h1 class="text-4xl font-bold">{displayCompany.display_name || displayCompany.name}</h1>
				<span class="rounded-full bg-primary px-3 py-1 text-sm font-medium text-primary-foreground">
					{ticker}
				</span>
			</div>
			<div class="flex items-center space-x-4 text-sm text-muted-foreground">
				<!-- {#if displayCompany.cik}
					<Badge>CIK: {displayCompany.cik}</Badge>
				{/if} -->
				{#if displayCompany.sic_description}
					<span>{displayCompany.sic_description}</span>
				{/if}
				<!-- <div class="text-center">
					<div class="text-primary text-2xl font-bold">{displayCompany.cik || 'N/A'}</div>
					<div class="text-muted-foreground text-sm">CIK</div>
				</div>
				{#if displayCompany.exchanges && displayCompany.exchanges.length > 0}
					{#if displayCompany.sic_description}<span>•</span>{/if}
					<span>{displayCompany.exchanges.join(', ')}</span>
				{/if} -->
			</div>
		</div>
	</div>

	<!-- Section 1: Company Description -->
	<Card>
		<CardHeader>
			<CardTitle class="flex items-center space-x-2">
				<span>📋</span>
				<span>Company Description</span>
			</CardTitle>
			<CardDescription>
				Overview of {displayCompany.display_name || displayCompany.name}'s business and operations
			</CardDescription>
		</CardHeader>
		<CardContent class="space-y-4">
			{#if displayCompany.summary && displayCompany.summary.trim()}
				<MarkdownContent content={cleanContent(displayCompany.summary) || 'what'} />
			{:else}
				<p class="leading-relaxed text-muted-foreground">No description available.</p>
			{/if}

			<!-- <div class="grid grid-cols-2 gap-4 border-t pt-4 md:grid-cols-4">
				<div class="text-center">
					<div class="text-primary text-2xl font-bold">{displayCompany.tickers?.length || 0}</div>
					<div class="text-muted-foreground text-sm">Tickers</div>
				</div>
				<div class="text-center">
					<div class="text-primary text-2xl font-bold">
						{displayCompany.sic_description || 'Unknown'}
					</div>
					<div class="text-muted-foreground text-sm">Industry</div>
				</div>
				<div class="text-center">
					<div class="text-primary text-2xl font-bold">
						{displayCompany.entity_type || 'Company'}
					</div>
					<div class="text-muted-foreground text-sm">Type</div>
				</div>
			</div> -->
		</CardContent>
	</Card>

	<!-- Section 2: Financial Overview (TBD) -->
	<Card>
		<CardHeader>
			<CardTitle class="flex items-center space-x-2">
				<span>📊</span>
				<span>Financial Overview</span>
			</CardTitle>
			<CardDescription>Key financial metrics and performance indicators</CardDescription>
		</CardHeader>
		<CardContent>
			<Button
				size="sm"
				href="https://finance.yahoo.com/quote/{data.ticker}/"
				target="_blank"
				class="bg-purple-700 text-white"
			>
				<ExternalLink class="mr-2 h-4 w-4" />
				View on Yahoo! Finance
			</Button>
		</CardContent>

		<!-- <CardContent>
			<div class="py-12 text-center">
				<div class="mb-4 text-6xl">🚧</div>
				<h3 class="mb-2 text-xl font-semibold">Financial Overview Coming Soon</h3>
				<p class="text-muted-foreground mb-6">
					We're working on integrating comprehensive financial data and metrics.
				</p>
				<div class="text-muted-foreground text-sm">
					This section will include:
					<ul class="mt-2 list-inside list-disc space-y-1">
						<li>Revenue and earnings trends</li>
						<li>Key financial ratios</li>
						<li>Balance sheet highlights</li>
						<li>Cash flow analysis</li>
					</ul>
				</div>
			</div>
		</CardContent> -->
	</Card>

	<!-- Section 3: Links to Filings / Analysis -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- AI Analysis -->
		<Card>
			<CardHeader>
				<CardTitle class="flex items-center space-x-2">
					<span>🤖</span>
					<span>LLM Analysis</span>
				</CardTitle>
				<CardDescription>
					LLM-generated insights and analysis for {displayCompany.display_name ||
						displayCompany.name}
				</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				{#if generatedContent.length > 0}
					<div class="space-y-3">
						{#each generatedContent as content}
							<div
								class="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted"
							>
								<div class="flex-1">
									<div class="text-sm font-medium">
										{getAnalysisTypeDisplay(content.document_type)} Analysis
									</div>
									<div class="flex items-center space-x-2 text-xs text-muted-foreground">
										<span class="rounded bg-secondary px-2 py-1 text-xs text-secondary-foreground">
											Content Generated on {formatDate(content.created_at)}
										</span>
									</div>
								</div>
								<Button
									variant="outline"
									size="sm"
									onclick={() => handleAnalysisClick(content.id, content.short_hash)}
								>
									View
								</Button>
							</div>
						{/each}
					</div>
				{:else}
					<div class="py-8 text-center">
						<div class="mb-4 text-muted-foreground">No analysis available yet</div>
						<p class="text-sm text-muted-foreground">
							Analysis will be generated from company filings and documents.
						</p>
					</div>
				{/if}

				<!-- <div class="border-t pt-4">
					<Button variant="outline" class="w-full" onclick={handleBrowseAnalysis}>
						Browse All Analysis →
					</Button>
				</div> -->
			</CardContent>
		</Card>

		<!-- SEC Filings -->
		<Card>
			<CardHeader>
				<CardTitle class="flex items-center space-x-2">
					<span>📄</span>
					<span>SEC Filings</span>
				</CardTitle>
				<CardDescription>Recent regulatory filings and documents</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				{#if filings.length > 0}
					<div class="space-y-3">
						{#each filings as filing}
							<div
								class="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted"
							>
								<div class="flex-1">
									<div class="text-sm font-medium">
										{format_filing_in_list(filing)}
										<!-- {filing.filing_type} - {filing.period_of_report || 'Current Report'} -->
									</div>
									<!-- <div class="text-muted-foreground text-xs"> -->
									<!-- 	Filed: {formatDate(filing.filing_date)} -->
									<!-- </div> -->
								</div>
								<Button
									variant="outline"
									size="sm"
									onclick={() => handleFilingClick(filing.accession_number)}
								>
									View
								</Button>
							</div>
						{/each}
					</div>
				{:else}
					<div class="py-8 text-center">
						<div class="mb-4 text-muted-foreground">No filings available</div>
						<p class="text-sm text-muted-foreground">
							SEC filings will appear here when available for this company.
						</p>
					</div>
				{/if}

				<!-- <div class="border-t pt-4">
					<Button variant="outline" class="w-full" onclick={handleBrowseFilings}>
						Browse All Filings →
					</Button>
				</div> -->
			</CardContent>
		</Card>
	</div>
</div>
