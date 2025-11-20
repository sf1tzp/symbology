<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { FileText, ExternalLink, File, Folder, Bot } from '@lucide/svelte';
	import type { DocumentResponse, GeneratedContentResponse } from '$lib/generated-api-types';

	// Accept both document and generated content sources
	let { sources }: { sources?: (DocumentResponse | GeneratedContentResponse)[] } = $props();

	const dispatch = createEventDispatcher();

	// FIXME: Let's move away from event passing here
	// We should pass all the necessary url parts to the SourcesList component
	// Then call goto(...) within that component
	function handleSourceClick(source: DocumentResponse | GeneratedContentResponse) {
		// Check if this is a document or generated content based on the presence of certain fields
		if ('title' in source) {
			// This is a document
			const docSource = source as DocumentResponse;
			dispatch('sourceSelected', {
				type: 'document',
				id: docSource.id,
				filing_id: docSource.filing_id,
				content_hash: docSource.content_hash,
				short_hash: docSource.short_hash,
				name: docSource.title,
				// Include filing accession number if available for URL construction
				accession_number: docSource.filing?.accession_number
			});
		} else {
			// This is generated content
			const contentSource = source as GeneratedContentResponse;
			dispatch('sourceSelected', {
				type: 'generated_content',
				id: contentSource.id,
				content_hash: contentSource.content_hash,
				short_hash: contentSource.short_hash,
				company_id: contentSource.company_id,
				document_type: contentSource.document_type
			});
		}
	}

	function getSourceTypeDisplay(source: DocumentResponse | GeneratedContentResponse): string {
		if ('title' in source) {
			// This is a document
			const docSource = source as DocumentResponse;
			const name = docSource.title.toLowerCase();
			if (name.includes('10-k')) return '10-K';
			if (name.includes('10-q')) return '10-Q';
			if (name.includes('8-k')) return '8-K';
			if (name.includes('mda') || name.includes('management')) return 'MD&A';
			if (name.includes('risk')) return 'Risk Factors';
			if (name.includes('business')) return 'Business';
			return 'Document';
		} else {
			// This is generated content
			const contentSource = source as GeneratedContentResponse;
			switch (contentSource.document_type?.toUpperCase()) {
				case 'MANAGEMENT_DISCUSSION':
					return 'MD&A Analysis';
				case 'RISK_FACTORS':
					return 'Risk Analysis';
				case 'BUSINESS_DESCRIPTION':
					return 'Business Analysis';
				default:
					return 'Generated Content';
			}
		}
	}

	function getSourceName(source: DocumentResponse | GeneratedContentResponse): string {
		if ('title' in source) {
			return (source as DocumentResponse).title;
		} else {
			const contentSource = source as GeneratedContentResponse;
			return contentSource.document_type
				? `${getSourceTypeDisplay(contentSource)}`
				: 'Generated Content';
		}
	}

	function getSourceIcon(source: DocumentResponse | GeneratedContentResponse) {
		if ('title' in source) {
			return FileText;
		} else {
			return Bot;
		}
	}

	function truncateSourceName(name: string, maxLength: number = 50): string {
		if (name.length <= maxLength) return name;
		return name.substring(0, maxLength - 3) + '...';
	}

	function getSourceHash(source: DocumentResponse | GeneratedContentResponse): string | null {
		if ('content_hash' in source) {
			return source.content_hash;
		}
		return null;
	}
</script>

<div class="space-y-4">
	{#if sources && sources.length > 0}
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<Folder class="h-4 w-4 text-muted-foreground" />
				<span class="text-sm font-medium">Source Materials</span>
				<Badge variant="outline" class="text-xs">
					{sources.length}
				</Badge>
			</div>
		</div>

		<div class="space-y-3">
			{#each sources as source, index}
				<div class="space-y-2">
					{#if index > 0}
						<Separator />
					{/if}

					<div class="group rounded-lg border p-3 transition-colors hover:bg-muted/50">
						<div class="space-y-2">
							<!-- Document Type Badge -->
							<div class="flex items-start justify-between">
								<Badge variant="secondary" class="text-xs">
									{getSourceTypeDisplay(source)}
								</Badge>
								<Button
									variant="ghost"
									size="sm"
									onclick={() => handleSourceClick(source)}
									class="h-6 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
								>
									<ExternalLink class="h-3 w-3" />
								</Button>
							</div>

							<!-- Document Name -->
							<div class="flex items-start space-x-2">
								{#if getSourceIcon(source) === FileText}
									<FileText class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
								{:else}
									<Bot class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
								{/if}
								<div class="min-w-0 flex-1">
									<p class="text-sm leading-tight font-medium">
										{truncateSourceName(getSourceName(source))}
									</p>
									{#if getSourceHash(source)}
										<span class="font-mono text-xs text-muted-foreground">
											{getSourceHash(source)?.substring(0, 12)}
										</span>
									{/if}
								</div>
								<Button
									variant="outline"
									size="sm"
									onclick={() => handleSourceClick(source)}
									class="h-6 px-2 text-xs"
								>
									View
								</Button>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="flex items-center justify-center p-8">
			<div class="space-y-3 text-center">
				<div class="flex justify-center">
					<div class="rounded-full bg-muted p-3">
						<File class="h-6 w-6 text-muted-foreground" />
					</div>
				</div>
				<div class="space-y-1">
					<p class="text-sm font-medium">No source materials found</p>
					<p class="max-w-sm text-xs text-muted-foreground">
						This analysis may have been generated from aggregated data or other non-document
						sources.
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>
