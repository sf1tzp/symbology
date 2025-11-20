<script lang="ts">
	import { goto } from '$app/navigation';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import FilingDetail from '$lib/components/filings/FilingDetail.svelte';
	import DocumentsList from '$lib/components/documents/DocumentsList.svelte';
	import type { PageData } from './$types';
	import { Eye } from '@lucide/svelte';

	let { data }: { data: PageData } = $props();

	function handleBackToCompany() {
		if (data.company && data.company.ticker) {
			goto(`/c/${data.company.ticker}`);
		} else {
			goto('/');
		}
	}
</script>

<svelte:head>
	<title
		>Filing {data.filing?.form || 'Unknown'} - {data.company?.name || 'Unknown'} - Symbology</title
	>
	<meta
		name="description"
		content="SEC filing details and documents for {data.company?.name || 'company'}"
	/>
</svelte:head>

<div class="space-y-8">
	<Button variant="ghost" onclick={handleBackToCompany}>
		← Back to {data.company?.name || 'Company'}
	</Button>

	<!-- Filing Details -->
	{#if data.filing}
		<FilingDetail filing={data.filing} company={data.company || undefined} />

		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Documents</CardTitle>
			</CardHeader>
			<CardContent>
				<DocumentsList documents={data.documents} filing={data.filing} />
			</CardContent>
		</Card>
	{:else}
		<Card>
			<div class="flex justify-center p-8">
				<div class="text-center">
					<Eye class="mx-auto h-8 w-8 text-muted-foreground" />
					<p class="text-sm text-muted-foreground">No Filing Data</p>
				</div>
			</div>
		</Card>
	{/if}
</div>
