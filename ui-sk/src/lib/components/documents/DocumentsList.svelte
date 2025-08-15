<script lang="ts">
	import type { DocumentResponse } from '$lib/generated-api-types';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { FileText, Eye } from '@lucide/svelte';
	import { createEventDispatcher } from 'svelte';

	interface Props {
		documents: DocumentResponse[];
		filing?: any;
	}

	let { documents }: Props = $props();

	const dispatch = createEventDispatcher<{
		documentSelected: DocumentResponse;
	}>();

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

	// Helper function to truncate content for preview
	function getContentPreview(content: string | null): string {
		if (!content) return 'No content available';

		// Remove excessive whitespace and newlines
		const cleaned = content.replace(/\s+/g, ' ').trim();

		if (cleaned.length <= 200) return cleaned;
		return cleaned.substring(0, 200) + '...';
	}

	// Helper function to format document ID for display
	function formatDocumentId(id: string): string {
		return id.length > 8 ? `${id.substring(0, 8)}` : id;
	}

	// Helper function to get badge variant based on document type
	function getDocumentTypeBadgeVariant(
		documentName: string
	): 'default' | 'secondary' | 'destructive' | 'outline' {
		const name = documentName.toLowerCase();

		if (name.includes('10-k') || name.includes('10-q')) return 'default';
		if (name.includes('8-k')) return 'secondary';
		if (name.includes('exhibit') || name.includes('schedule')) return 'outline';

		return 'outline';
	}

	function handleDocumentClick(document: DocumentResponse) {
		dispatch('documentSelected', document);
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
</script>

{#if documents.length === 0}
	<div class="flex items-center justify-center p-8 text-center">
		<div>
			<FileText class="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
			<p class="text-muted-foreground">No documents found in this filing</p>
		</div>
	</div>
{:else}
	<div class="space-y-4">
		{#each documents as document (document.id)}
			<Card class="transition-colors hover:bg-muted/50">
				<CardHeader class="pb-3">
					<div class="flex items-start justify-between">
						<div class="space-y-2">
							<div class="flex items-center space-x-2">
								<FileText class="h-4 w-4 text-muted-foreground" />
								<CardTitle class="text-base">
									{getAnalysisTypeDisplay(document.document_type)}
								</CardTitle>
							</div>
							<div class="flex flex-wrap items-center gap-2">
								<!-- <Badge variant={getDocumentTypeBadgeVariant(document.document_name)}>
									{getDocumentTypeName(document.document_name)}
								</Badge> -->
								<Badge variant="outline" class="font-mono text-xs">
									{formatDocumentId(document.content_hash)}
								</Badge>
							</div>
						</div>
						<Button
							variant="outline"
							size="sm"
							onclick={() => handleDocumentClick(document)}
							class="ml-4"
						>
							<Eye class="mr-2 h-4 w-4" />
							View
						</Button>
					</div>
				</CardHeader>

				{#if document.content}
					<CardContent class="pt-0">
						<div class="text-sm text-muted-foreground">
							<p class="leading-relaxed">
								{getContentPreview(document.content)}
							</p>
						</div>
					</CardContent>
				{/if}
			</Card>
		{/each}

		<div class="mt-6 text-center">
			<p class="text-sm text-muted-foreground">
				{documents.length} document{documents.length === 1 ? '' : 's'} in this filing
			</p>
		</div>
	</div>
{/if}
