<script lang="ts">
	import type { FilingResponse, CompanyResponse } from '$lib/generated-api-types';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ExternalLink } from '@lucide/svelte';

	interface Props {
		filing: FilingResponse;
		company?: CompanyResponse;
	}

	let { filing, company }: Props = $props();

	// Helper function to format dates
	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	// Helper function to get filing type label
	function getFilingTypeLabel(filingType: string): string {
		const labels: Record<string, string> = {
			'10-K': 'Annual Report',
			'10-Q': 'Quarterly Report',
			'8-K': 'Current Report',
			'DEF 14A': 'Proxy Statement',
			'S-1': 'Registration Statement',
			'20-F': 'Annual Report (Foreign)'
		};
		return labels[filingType] || filingType;
	}

	// Helper function to format document ID for display
	function formatDocumentId(id: string): string {
		return id.length > 8 ? `${id.substring(0, 8)}...` : id;
	}

	// Prepare filing meta items
	const filingMetaItems = $derived([
		{ label: 'Filing Type', value: getFilingTypeLabel(filing.filing_type) },
		{ label: 'Filing Date', value: formatDate(filing.filing_date) },
		...(filing.period_of_report
			? [{ label: 'Period of Report', value: formatDate(filing.period_of_report) }]
			: []),
		{ label: 'Accession Number', value: filing.accession_number },
		{ label: 'Filing ID', value: formatDocumentId(filing.id) }
	]);
	function formatYear(dateString: string): string {
		try {
			return new Date(dateString).getFullYear().toString();
		} catch {
			return dateString;
		}
	}

	// Prepare header display text
	const headerTitle = $derived(() => {
		const companyName = company?.display_name || company?.name || 'Company';
		const filingType = filing.filing_type;
		const periodEnd = filing.period_of_report ? formatYear(filing.period_of_report) : null;

		if (periodEnd) {
			return `${periodEnd} ${filingType}`;
		} else {
			return `${companyName} ${filingType}`;
		}
	});
</script>

<Card>
	<CardHeader>
		<div class="flex items-start justify-between">
			<div>
				<CardTitle class="text-xl">{headerTitle()}</CardTitle>
				<div class="mt-2 flex flex-wrap items-center gap-2">
					<Badge variant="secondary" class="bg-gray-500 text-white"
						>{company?.tickers?.[0] ?? 'N/A'}</Badge
					>
					<Badge variant="default">{getFilingTypeLabel(filing.filing_type)}</Badge>
					<Badge variant="outline">Filed on {formatDate(filing.filing_date)}</Badge>
				</div>
			</div>
			{#if filing.filing_url}
				<Button variant="outline" size="sm" href={filing.filing_url} target="_blank">
					<ExternalLink class="mr-2 h-4 w-4" />
					View on sec.gov
				</Button>
			{/if}
		</div>
	</CardHeader>
	<!-- <CardContent>
		<div class="space-y-4">
			<div>
				<h3 class="text-muted-foreground mb-2 text-sm font-medium">Filing Information</h3>
				<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
					{#each filingMetaItems as item}
						<div class="border-border flex justify-between border-b pb-1">
							<span class="text-muted-foreground">{item.label}:</span>
							<span
								class="text-right font-medium {item.label === 'Filing ID' ||
								item.label === 'Accession Number'
									? 'font-mono text-xs'
									: ''}">{item.value}</span
							>
						</div>
					{/each}
				</div>
			</div>

			{#if company}
				<div>
					<h3 class="text-muted-foreground mb-2 text-sm font-medium">Company Information</h3>
					<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
						<div class="border-border flex justify-between border-b pb-1">
							<span class="text-muted-foreground">Name:</span>
							<span class="text-right font-medium">{company.name}</span>
						</div>
						{#if company.tickers && company.tickers.length > 0}
							<div class="border-border flex justify-between border-b pb-1">
								<span class="text-muted-foreground">Ticker:</span>
								<span class="text-right font-medium">{company.tickers.join(', ')}</span>
							</div>
						{/if}
						{#if company.cik}
							<div class="border-border flex justify-between border-b pb-1">
								<span class="text-muted-foreground">CIK:</span>
								<span class="text-right font-mono text-xs font-medium">{company.cik}</span>
							</div>
						{/if}
						{#if company.sic_description}
							<div class="border-border flex justify-between border-b pb-1">
								<span class="text-muted-foreground">Industry:</span>
								<span class="text-right font-medium">{company.sic_description}</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</CardContent> -->
</Card>
