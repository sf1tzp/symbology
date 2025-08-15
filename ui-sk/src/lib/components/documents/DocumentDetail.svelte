<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { FileText, Calendar, Hash, HandCoins } from '@lucide/svelte';
	import MarkdownContent from '../ui/MarkdownContent.svelte';
	import Separator from '../ui/separator/separator.svelte';
	import { badgeVariants } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button';
	import type { DocumentResponse } from '$lib/generated-api-types';
	import { ExternalLink } from '@lucide/svelte';

	interface Props {
		document: DocumentResponse;
	}

	let { document }: Props = $props();

	// Helper function to get document type name from document name
	function getDocumentTypeName(documentName: string): string {
		const name = documentName.toLowerCase();

		if (name.includes('10-k') || name.includes('10k')) return '10-K Annual Report';
		if (name.includes('10-q') || name.includes('10q')) return '10-Q Quarterly Report';
		if (name.includes('8-k') || name.includes('8k')) return '8-K Current Report';
		if (name.includes('def') && name.includes('14a')) return 'DEF 14A Proxy Statement';
		if (name.includes('s-1') || name.includes('s1')) return 'S-1 Registration Statement';
		if (name.includes('20-f') || name.includes('20f')) return '20-F Annual Report';

		// Extract specific document types from common patterns
		if (name.includes('exhibit')) return 'Exhibit';
		if (name.includes('cover')) return 'Cover Page';
		if (name.includes('table') && name.includes('contents')) return 'Table of Contents';
		if (name.includes('signature')) return 'Signatures';
		if (name.includes('financial') || name.includes('statement')) return 'Financial Statement';
		if (name.includes('note')) return 'Notes';
		if (name.includes('schedule')) return 'Schedule';

		// Default to the document name itself
		return documentName;
	}

	function estimateTokens(content: string) {
		// Rough estimation: ~4 characters per token for English text
		return Math.ceil(content.length / 4);
	}

	// Format content for display
	function formatContent(content: string): string {
		if (!content) return 'No content available';

		// Basic HTML content cleanup and formatting
		return content
			.replace(/<[^>]*>/g, '') // Remove HTML tags
			.replace(/\s+/g, ' ') // Normalize whitespace
			.trim();
	}

	// Get content preview
	function getContentPreview(content: string, maxLength: number = 500): string {
		const formatted = formatContent(content);
		if (formatted.length <= maxLength) return formatted;
		return formatted.substring(0, maxLength) + '...';
	}
</script>

<Card class="h-full w-full">
	<CardHeader>
		<div class="flex items-start justify-between">
			<div class="flex items-center space-x-2">
				<FileText class="h-5 w-5 text-muted-foreground" />
				<div>
					<CardTitle class="text-lg">Document Content:</CardTitle>
				</div>
			</div>
			<!-- <div class="flex flex-wrap gap-2"> -->
			<!-- {#if document.filing} -->
			<!-- 	<Badge variant="outline" class="flex items-center space-x-1"> -->
			<!-- 		<Calendar class="h-3 w-3" /> -->
			<!-- 		<span>Filed on: {new Date(document.filing.filing_date).toLocaleDateString()}</span> -->
			<!-- 	</Badge> -->
			<!-- {/if} -->

			<!-- <Button variant="outline" size="sm" href={document.filing.filing_url} target="_blank">
					<ExternalLink class="mr-2 h-4 w-4" />
					View on sec.gov
				</Button> -->
			<!-- </div> -->
		</div>
	</CardHeader>
	<CardContent>
		<div class="space-y-4">
			<!-- Content preview -->
			<!-- <div class="text-muted-foreground text-sm">
				<p class="mb-2 font-medium">Content Preview:</p>
				<div class="bg-muted/50 max-h-32 overflow-y-auto rounded-md p-3">
					{getContentPreview(document.content)}
				</div>
			</div> -->
			<!-- Document metadata -->
			<!-- {#if document.filing}
				<div class="border-t pt-4">
					<p class="mb-2 text-sm font-medium">Document Details:</p>
					<div class="text-muted-foreground grid grid-cols-2 gap-2 text-sm">
						<div>Filing Type: {document.filing.filing_type}</div>
						<div>Filing Date: {new Date(document.filing.filing_date).toLocaleDateString()}</div>
						<div>Accession: {document.filing.accession_number}</div>
						{#if document.filing.period_of_report}
							<div>
								Period of Report: {new Date(document.filing.period_of_report).toLocaleDateString()}
							</div>
						{/if}
					</div>
				</div>
			{/if} -->

			<Separator />
			<div
				class="mt-3 max-h-96 overflow-y-auto rounded-md bg-muted/30 p-4 text-sm whitespace-pre-wrap"
			>
				<MarkdownContent content={document.content} />
			</div>
			<Separator />

			<!-- Full content (expandable) -->
			<!-- <details class="mt-4"> -->
			<!-- 	<summary class="hover:text-primary cursor-pointer text-sm font-medium"> -->
			<!-- 		<span> View Full Content </span> -->
			<!-- 		<span class="text-muted-foreground ml-2 text-xs"> -->
			<!-- 			({getContentPreview(document.content, 100)}) -->
			<!-- 		</span> -->
			<!-- 	</summary> -->
			<!-- 	<div -->
			<!-- 		class="bg-muted/30 mt-3 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-md p-4 text-sm" -->
			<!-- 	> -->
			<!-- 		<MarkdownContent content={document.content} /> -->
			<!-- 	</div> -->
			<!-- </details> -->
		</div>
	</CardContent>
</Card>
