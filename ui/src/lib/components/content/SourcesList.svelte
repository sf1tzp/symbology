<script lang="ts">
	import { goto } from '$app/navigation';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { FileText, ExternalLink, File, Folder, Bot } from '@lucide/svelte';
	import type { DocumentResponse, GeneratedContentResponse } from '$lib/generated-api-types';
	import Card from '../ui/card/card.svelte';
	import { titleCase } from 'title-case';
	import CardContent from '../ui/card/card-content.svelte';

	// Accept both document and generated content sources, plus ticker for URL construction
	let {
		sources,
		ticker
	}: {
		sources?: (DocumentResponse | GeneratedContentResponse)[];
		ticker: string;
	} = $props();

	function handleSourceClick(source: DocumentResponse | GeneratedContentResponse) {
		// Check if this is a document or generated content based on the presence of certain fields
		if ('title' in source) {
			// This is a document
			const docSource = source as DocumentResponse;
			// For documents, prefer the accession number + content hash route if available
			if (docSource.filing?.accession_number && docSource.content_hash) {
				const shortHash = docSource.short_hash || docSource.content_hash.substring(0, 12);
				goto(`/d/${docSource.filing.accession_number}/${shortHash}`);
			} else {
				// Fallback to simple document viewer by ID
				goto(`/documents/${docSource.id}`);
			}
		} else {
			// This is generated content
			const contentSource = source as GeneratedContentResponse;
			// For generated content, navigate to the content view using ticker and hash
			if (contentSource.short_hash) {
				goto(`/g/${ticker}/${contentSource.short_hash}`);
			} else if (contentSource.content_hash) {
				// Use first 12 characters of full hash if short hash not available
				const shortHash = contentSource.content_hash.substring(0, 12);
				goto(`/g/${ticker}/${shortHash}`);
			}
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
			return contentSource.description
				? `${titleCase(contentSource.description.replace(/[_]/g, ' '))}`
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
</script>

{#if sources && sources.length > 0}
	<div class="mb-4">
		<div class="flex items-center space-x-2">
			<Folder class="h-4 w-4 text-muted-foreground" />
			<span class="text-sm font-medium">Source Materials</span>
			<Badge variant="outline" class="text-xs">
				{sources.length}
			</Badge>
		</div>
	</div>

	{#each sources as source, index}
		<Card onclick={() => handleSourceClick(source)} class="mb-4 last:mb-auto">
			<CardContent>
				<!-- Document Name -->
				<div class="flex items-start justify-between">
					<div class="flex items-start justify-between">
						{#if getSourceIcon(source) === FileText}
							<FileText class="mr-2 -ml-4 text-muted-foreground md:my-auto" />
						{:else}
							<Bot class="mr-2 -ml-4 text-muted-foreground" />
						{/if}
						<div class="">
							<p class="text-sm leading-tight font-medium">
								{truncateSourceName(getSourceName(source))}
							</p>
							<span class="font-mono text-xs text-muted-foreground">
								{source.short_hash}
							</span>
						</div>
					</div>
					<Button
						variant="outline"
						size="sm"
						onclick={() => handleSourceClick(source)}
						class="ml-4"
					>
						View
					</Button>
				</div>
			</CardContent>
		</Card>
	{/each}
{:else}
	<div class="flex items-center justify-center p-8">
		<div class="space-y-4 text-center">
			<div class="flex justify-center">
				<div class="rounded-full bg-muted p-4">
					<File class="h-8 w-8 text-muted-foreground" />
				</div>
			</div>
			<div class="space-y-2">
				<p class="text-sm font-medium">No source materials found</p>
				<p class="max-w-sm text-xs text-muted-foreground">
					This analysis may have been generated from aggregated data or other non-document sources.
				</p>
			</div>
		</div>
	</div>
{/if}
