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
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function handleBackToFiling() {
		if (data.filing) {
			goto(`/f/${data.filing.edgar_id}`);
		} else {
			handleBackToCompany();
		}
	}

	function handleBackToCompany() {
		if (data.company && data.company.tickers.length > 0) {
			goto(`/c/${data.company.tickers[0]}`);
		} else {
			goto('/');
		}
	}
</script>

<svelte:head>
	<title>{data.document.document_name} - {data.company?.name || 'Unknown'} - Symbology</title>
	<meta
		name="description"
		content="SEC document details and content for {data.company?.name || 'company'}"
	/>
</svelte:head>

<div class="space-y-6">
	<!-- Header with navigation -->
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-2">
			<Button variant="ghost" onclick={handleBackToFiling}>← Back to Filing</Button>
			<Button variant="ghost" onclick={handleBackToCompany}>
				← Back to {data.company?.name || 'Company'}
			</Button>
		</div>
		<div class="flex items-center space-x-2">
			<Badge variant="outline">{data.document.document_type}</Badge>
			<Badge variant="secondary">ID: {data.edgar_id.substring(0, 8)}</Badge>
		</div>
	</div>

	<!-- Document Title -->
	<div>
		<h1 class="text-2xl font-bold">{data.document.document_name}</h1>
		<p class="text-muted-foreground mt-1">
			From {data.filing?.filing_type} filing on {data.filing?.filing_date}
		</p>
	</div>

	<!-- Document Content -->
	<DocumentDetail document={data.document} />
</div>
