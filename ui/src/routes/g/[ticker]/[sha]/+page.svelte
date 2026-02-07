<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Calendar, Clock, HandCoins } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge, badgeVariants } from '$lib/components/ui/badge';
	import ContentViewer from '$lib/components/content/ContentViewer.svelte';
	import SourcesList from '$lib/components/content/SourcesList.svelte';
	import ModelConfig from '$lib/components/content/ModelConfig.svelte';
	import type { PageData } from './$types';
	import Separator from '$lib/components/ui/separator/separator.svelte';

	let { data }: { data: PageData } = $props();

	function handleBackToCompany() {
		goto(`/c/${data.ticker}`);
	}
	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDuration(duration: number | null): string {
		if (!duration) return 'N/A';
		if (duration < 60) return `${duration.toFixed(1)}s`;
		const minutes = Math.floor(duration / 60);
		const seconds = Math.floor(duration % 60);
		return `${minutes}m ${seconds}s`;
	}

	function estimateTokens(content: string) {
		// Rough estimation: ~4 characters per token for English text
		return Math.ceil(content.length / 4);
	}

	function getContentTitle(): string {
		if (data.content.document_type) {
			return `${getAnalysisTypeDisplay(data.content.document_type)} Analysis`;
		}
		return 'Generated Analysis';
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
</script>

<svelte:head>
	<title>{getContentTitle()} - {data.company.name} - Symbology</title>
	<meta name="description" content="LLM-generated analysis for {data.company.name}" />
</svelte:head>

<div class="space-y-8">
	<!-- Header with navigation -->
	<div class="flex items-center justify-between">
		<Button variant="ghost" onclick={handleBackToCompany}>
			← Back to {data.company.name}
		</Button>
	</div>

	<div class="flex items-center space-x-4">
		<h1 class="text-2xl font-bold">{getContentTitle()}</h1>
		<Badge variant="secondary" class="bg-gray-500 text-white">{data.ticker}</Badge>
		<a href="/g/{data.ticker}/{data.sha}" class={badgeVariants({ variant: 'secondary' })}>
			<span class="font-mono">{data.sha}</span>
		</a>
	</div>

	<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
		<div class="space-y-4">
			<!-- Model Configuration -->
			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Model Configuration</CardTitle>
				</CardHeader>
				<CardContent>
					{#if data.content?.modelConfig}
						<ModelConfig config={data.content.modelConfig} />
					{/if}
				</CardContent>
			</Card>

			<!-- Sources -->
			<Card>
				<CardContent>
					{#if data.content?.sources}
						<SourcesList sources={data.content.sources} ticker={data.ticker} />
					{/if}
				</CardContent>
			</Card>
		</div>

		<!-- Main Content -->
		<div class="lg:col-span-2">
			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Generated Content</CardTitle>
					{#if data.content?.input_tokens || data.content?.output_tokens}
						<div class="flex text-sm text-muted-foreground">
							<HandCoins class="mr-2 h-4 w-4" />
							{#if data.content.input_tokens}{data.content.input_tokens.toLocaleString()} input{/if}{#if data.content.input_tokens && data.content.output_tokens}
								/
							{/if}{#if data.content.output_tokens}{data.content.output_tokens.toLocaleString()} output{/if}
							tokens
						</div>
					{:else if data.content?.content}
						<div class="flex text-sm text-muted-foreground">
							<HandCoins class="mr-2 h-4 w-4" />
							~{estimateTokens(data.content.content || '')} tokens (estimated)
						</div>
					{/if}

					{#if data.content?.content}
						<div class="flex text-sm text-muted-foreground">
							<Calendar class="mr-2 h-4 w-4" />
							Generated {formatDate(data.content.created_at)}
						</div>
					{/if}
					{#if data.content.total_duration}
						<div class="flex text-sm text-muted-foreground">
							<Clock class="mr-2 h-4 w-4" />
							Completed in {formatDuration(data.content.total_duration)}
						</div>
					{/if}
				</CardHeader>
				<CardContent>
					<Separator class="mb-8" />
					<ContentViewer content={data.content} />
				</CardContent>
			</Card>
		</div>
	</div>
</div>
