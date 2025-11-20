<script lang="ts">
	import type { DocumentResponse, FilingResponse } from '$lib/generated-api-types';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { FileText, Eye } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { titleCase } from 'title-case';

	interface Props {
		documents: DocumentResponse[];
		filing?: any;
	}

	let { documents, filing }: Props = $props();

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

	function handleDocumentClick(filing: FilingResponse, document: DocumentResponse) {
		goto(`/d/${filing.accession_number}/${document.short_hash}`);
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

		return titleCase(type);
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
			<Card
				class="transition-colors hover:bg-muted/50"
				onclick={() => handleDocumentClick(filing, document)}
			>
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
								<Badge variant="outline" class="font-mono text-xs">
									{document.short_hash || formatDocumentId(document.content_hash)}
								</Badge>
							</div>
						</div>
						<Button
							variant="outline"
							size="sm"
							onclick={() => handleDocumentClick(filing, document)}
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
				We processed {documents.length} document{documents.length === 1 ? '' : 's'} from this filing
			</p>
		</div>
	</div>
{/if}
