<script lang="ts">
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
	import type { FilingResponse } from '$lib/generated-api-types';

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
		const type = documentType?.toLowerCase() ?? '';

		// Core document types
		if (type.includes('management_discussion')) return 'Management Discussion';
		if (type.includes('risk_factors')) return 'Risk Factors';
		if (type.includes('business_description')) return 'Business Description';

		// Additional document sections
		if (type.includes('controls_procedures')) return 'Controls & Procedures';
		if (type.includes('legal_proceedings')) return 'Legal Proceedings';
		if (type.includes('market_risk')) return 'Market Risk';
		if (type.includes('executive_compensation')) return 'Executive Compensation';
		if (type.includes('directors_officers')) return 'Directors & Officers';

		return documentType;
	}

	function format_filing_period(filing: FilingResponse) {
		let fye = new Date(company?.fiscal_year_end);
		let reportDate = new Date(filing.period_of_report);

		try {
			const reportMonth = reportDate.getMonth() + 1; // getMonth returns 0-11
			const reportYear = reportDate.getFullYear();

			if (filing.form.includes('10-Q')) {
				// Determine quarter based on fiscal year end
				let quarter: number;
				let fiscalYear: number;

				if (fye) {
					// Parse fiscal year end (format like "1231" for Dec 31)
					const fyeMonth = fye.getMonth() + 1;
					const fyeDay = fye.getDay() + 1;

					// Calculate which fiscal year this report belongs to
					// If report date is after fiscal year end, it's the next fiscal year
					const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);
					const fyeLastYear = new Date(reportYear - 1, fyeMonth - 1, fyeDay);

					if (reportDate > fyeThisYear) {
						fiscalYear = reportYear + 1;
					} else if (reportDate > fyeLastYear) {
						fiscalYear = reportYear;
					} else {
						fiscalYear = reportYear - 1;
					}

					// Calculate quarter based on months from fiscal year end
					const monthsFromFYE = (reportMonth - fyeMonth + 12) % 12;
					if (monthsFromFYE >= 0 && monthsFromFYE < 3) {
						quarter = 1;
					} else if (monthsFromFYE < 6) {
						quarter = 2;
					} else if (monthsFromFYE < 9) {
						quarter = 3;
					} else {
						quarter = 4;
					}
				} else {
					// Fall back to calendar year quarters
					fiscalYear = reportYear;
					if (reportMonth <= 3) {
						quarter = 1;
					} else if (reportMonth <= 6) {
						quarter = 2;
					} else if (reportMonth <= 9) {
						quarter = 3;
					} else {
						quarter = 4;
					}
				}

				return `Fiscal Year ${fiscalYear} Q${quarter}`;
			}

			if (filing.form.includes('10-K')) {
				let fiscalYear = reportYear;

				// For 10-K, determine the fiscal year based on fiscal year end
				if (fye) {
					const fyeMonth = fye.getMonth() + 1;
					const fyeDay = fye.getDay();
					const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);

					// If report date is close to fiscal year end, it's likely that fiscal year
					// Otherwise, it might be the previous fiscal year
					if (reportDate >= fyeThisYear) {
						fiscalYear = reportYear;
					} else {
						fiscalYear = reportYear;
					}
				}

				return `Fiscal Year ${fiscalYear}`;
			}
		} catch (error) {
			// If date parsing fails, fall back to original date string
			console.warn('Failed to parse filing date:', reportDate, error);
		}

		return reportDate;
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
				{#if displayCompany.sic_description}
					<span>{displayCompany.sic_description}</span>
				{/if}
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
	</Card>

	<!-- Section 3: Links to Filings / Analysis -->
	<div class="grid grid-cols-1 gap-8 lg:grid-cols-2">
		<!-- LLM Analysis -->
		<Card>
			<CardHeader>
				<CardTitle class="flex items-center space-x-2">
					<span>🤖</span>
					<span>AI Analysis Summaries</span>
				</CardTitle>
				<CardDescription>
					High-level LLM-generated summaries and insights for {displayCompany.display_name ||
						displayCompany.name}
				</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				{#if generatedContent.length > 0}
					{#each generatedContent as content}
						<Card
							class="transition-shadow hover:bg-muted/50 hover:shadow-md"
							onclick={() => handleAnalysisClick(content.id, content.short_hash)}
						>
							<CardContent>
								<div class="flex justify-between">
									<div class="">
										<div class="text-sm font-medium">
											{getAnalysisTypeDisplay(content.document_type)} Summary
										</div>
										<div class="text-xs text-muted-foreground">
											Content Generated on {formatDate(content.created_at)}
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
							</CardContent>
						</Card>
					{/each}
				{:else}
					<div class="py-8 text-center">
						<div class="mb-4 text-muted-foreground">No analysis summaries available yet</div>
						<p class="text-sm text-muted-foreground">
							Analysis summaries will be generated from company filings and documents.
						</p>
					</div>
				{/if}
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
					<div class="space-y-4">
						{#each filings as filing}
							<Card
								class="transition-shadow hover:bg-muted/50 hover:shadow-md"
								onclick={() => handleFilingClick(filing.accession_number)}
							>
								<CardContent>
									<div class="flex justify-between">
										<div class="">
											<div class="text-sm font-medium">
												{company?.display_name}'s {filing.form}
											</div>
											<div class="text-xs text-muted-foreground">
												{format_filing_period(filing)}
											</div>
										</div>
										<Button
											variant="outline"
											size="sm"
											onclick={() => handleFilingClick(filing.accession_number)}
										>
											View
										</Button>
									</div>
								</CardContent>
							</Card>
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
			</CardContent>
		</Card>
	</div>
</div>
