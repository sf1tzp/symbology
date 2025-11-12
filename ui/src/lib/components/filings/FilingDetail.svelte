<script lang="ts">
	import type { FilingResponse, CompanyResponse } from '$lib/generated-api-types';
	import { Card, CardHeader, CardTitle } from '$lib/components/ui/card';
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
		const filingType = filing.form;
		const periodOfReport = filing.period_of_report;

		if (periodOfReport) {
			return `${periodOfReport} ${filingType}`;
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
					<Badge variant="secondary" class="bg-gray-500 text-white">{company?.ticker}</Badge>
					<Badge variant="default">{getFilingTypeLabel(filing.form)}</Badge>
					<Badge variant="outline">Filed on {formatDate(filing.filing_date)}</Badge>
				</div>
			</div>
			{#if filing.url}
				<Button variant="outline" size="sm" href={filing.url} target="_blank">
					<ExternalLink class="mr-2 h-4 w-4" />
					View on sec.gov
				</Button>
			{/if}
		</div>
	</CardHeader>
</Card>
