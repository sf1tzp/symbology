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
	import { Badge, badgeVariants } from '$lib/components/ui/badge';
	import ContentViewer from '$lib/components/content/ContentViewer.svelte';
	import SourcesList from '$lib/components/content/SourcesList.svelte';
	import ModelConfig from '$lib/components/content/ModelConfig.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function handleBackToCompany() {
		goto(`/c/${data.ticker}`);
	}

	function handleSourceSelected(event: CustomEvent) {
		const source = event.detail;
		if (source.type === 'document' && source.edgar_id) {
			goto(`/d/${source.edgar_id}`);
		} else if (source.type === 'filing' && source.edgar_id) {
			goto(`/f/${source.edgar_id}`);
		}
	}

	function getContentTitle(): string {
		if (data.content.document_type) {
			return `${data.content.document_type} Analysis`;
		}
		return 'Generated Analysis';
	}
</script>

<svelte:head>
	<title>{getContentTitle()} - {data.company.name} - Symbology</title>
	<meta name="description" content="AI-generated analysis for {data.company.name}" />
</svelte:head>

<div class="space-y-6">
	<!-- Header with navigation -->
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-4">
			<Button variant="ghost" onclick={handleBackToCompany}>
				← Back to {data.company.name}
			</Button>
			<div>
				<h1 class="text-2xl font-bold">{getContentTitle()}</h1>
				<div class="mt-1 flex items-center space-x-2">
					<Badge variant="outline">{data.ticker}</Badge>
					<a href="/g/{data.ticker}/{data.sha}" class={badgeVariants({ variant: 'secondary' })}>
						<span class="font-mono">{data.sha}</span>
					</a>
					{#if data.content.document_type}
						<Badge variant="default">{data.content.document_type}</Badge>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Content Grid -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
		<!-- Main Content -->
		<div class="space-y-6 lg:col-span-2">
			<Card>
				<CardHeader>
					<CardTitle>Generated Content</CardTitle>
					<CardDescription>AI-generated analysis based on source materials</CardDescription>
				</CardHeader>
				<CardContent>
					<ContentViewer content={data.content} />
				</CardContent>
			</Card>
		</div>

		<!-- Sidebar -->
		<div class="space-y-6">
			<!-- Model Configuration -->
			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Model Configuration</CardTitle>
				</CardHeader>
				<CardContent>
					<ModelConfig config={data.content.modelConfig} />
				</CardContent>
			</Card>

			<!-- Sources -->
			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Source Materials</CardTitle>
					<CardDescription>Documents and data used to generate this content</CardDescription>
				</CardHeader>
				<CardContent>
					<SourcesList sources={data.content.sources} on:sourceSelected={handleSourceSelected} />
				</CardContent>
			</Card>
		</div>
	</div>
</div>
