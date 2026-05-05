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
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import DocumentDetail from '$lib/components/documents/DocumentDetail.svelte';
	import type { DocumentResponse } from '$lib/api-types';
	import { badgeVariants } from '$lib/components/ui/badge/index.js';
	import { ExternalLink, HandCoins } from '@lucide/svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function handleBackToFiling() {
		if (data.document.filing && data.document.filing.accession_number) {
			goto(`/f/${data.document.filing.accession_number}`);
		} else {
			goto('/filings');
		}
	}

	function handleBackToCompany() {
		if (data.document.filing && data.document.company_ticker) {
			// Note: We'd need to fetch company details or include ticker in the response
			// For now, navigate to companies list
			goto(`/c/${data.document.company_ticker}`);
		} else {
			goto('/companies');
		}
	}

	function formatYear(dateString: string): string {
		try {
			return new Date(dateString).getFullYear().toString();
		} catch {
			return dateString;
		}
	}
	function estimateTokens(content: string) {
		// Rough estimation: ~4 characters per token for English text
		return Math.ceil(content.length / 4);
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

	function formatTitle(document: DocumentResponse): string {
		const type = getAnalysisTypeDisplay(document.document_type);
		const year = document.filing?.period_of_report
			? formatYear(document.filing.period_of_report)
			: '';
		return `${document.company_ticker}. ${year} ${type}`;
	}

	// Get short hash for display
	const shortHash = data.document.short_hash || data.content_hash.substring(0, 8);
</script>

<svelte:head>
	<title>{data.document.title} - Symbology</title>
	<meta name="description" content="SEC document details and content" />
</svelte:head>

<div class="space-y-8">
	<!-- Header with navigation -->
	<div class="flex items-center justify-between">
		<div class="flex space-x-2">
			<Button variant="ghost" onclick={handleBackToFiling}>← Back to Filing</Button>
			<Button variant="ghost" onclick={handleBackToCompany}>← Back to Company</Button>
		</div>
	</div>

	<!-- Document Title -->
	<h1 class="text-2xl font-bold">{formatTitle(data.document)}</h1>
	<div class="flex space-x-4">
		<Badge variant="secondary" class="bg-muted-foreground p-2 text-white"
			>{data.document.company_ticker}</Badge
		>
		<a
			href="/d/{data.accession_number}/{shortHash}"
			class={badgeVariants({ variant: 'secondary', class: 'rounded-md p-2' })}
		>
			<span class="font-mono">{shortHash}</span>
		</a>
	</div>

	<!-- Document Content -->
	<DocumentDetail document={data.document} />
</div>
