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
	import FilingDetail from '$lib/components/filings/FilingDetail.svelte';
	import DocumentsList from '$lib/components/documents/DocumentsList.svelte';
	import type { PageData } from './$types';
	import type { DocumentResponse } from '$lib/generated-api-types';

	let { data }: { data: PageData } = $props();

	function handleBackToCompany() {
		if (data.company && data.company.tickers && data.company.tickers.length > 0) {
			goto(`/c/${data.company.tickers[0]}`);
		} else {
			goto('/');
		}
	}

	function handleDocumentSelected(event: CustomEvent<DocumentResponse>) {
		const hash = event.detail.content_hash.substring(0, 12);
		goto(`/d/${data.accession_number}/${event.detail.content_hash}`);
	}
</script>

<svelte:head>
	<title
		>Filing {data.filing?.filing_type || 'Unknown'} - {data.company?.name || 'Unknown'} - Symbology</title
	>
	<meta
		name="description"
		content="SEC filing details and documents for {data.company?.name || 'company'}"
	/>
</svelte:head>

<div class="space-y-6">
	<!-- Header with navigation -->
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-4">
			<Button variant="ghost" onclick={handleBackToCompany}>
				← Back to {data.company?.name || 'Company'}
			</Button>
			<div>
				<!-- <h1 class="text-2xl font-bold">
					{data.filing.filing_type} Filing
				</h1> -->
				<!-- <div class="mt-1 flex items-center space-x-2">
					<Badge variant="outline">{data.filing.filing_date}</Badge>
					<Badge variant="secondary">ID: {data.accession_number.substring(0, 8)}</Badge>
				</div> -->
			</div>
		</div>
	</div>

	<!-- Filing Details -->
	{#if data.filing}
		<FilingDetail filing={data.filing} company={data.company || undefined} />
	{/if}

	<!-- Documents -->
	<Card>
		<CardHeader>
			<CardTitle class="text-lg">Filing Documents</CardTitle>
			<CardDescription>Documents contained within this SEC filing</CardDescription>
		</CardHeader>
		<CardContent>
			<DocumentsList documents={data.documents} on:documentSelected={handleDocumentSelected} />
		</CardContent>
	</Card>
</div>
