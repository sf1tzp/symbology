<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { FileText, ExternalLink, File, Folder } from '@lucide/svelte';
	import type { MockDocument } from '$lib/mockData';

	let { sources }: { sources?: MockDocument[] } = $props();

	const dispatch = createEventDispatcher();

	function handleSourceClick(source: MockDocument) {
		// Emit event with source information
		dispatch('sourceSelected', {
			type: 'document',
			id: source.id,
			filing_id: source.filing_id,
			edgar_id: source.filing_id, // Assuming filing_id can be used as edgar_id
			name: source.document_name
		});
	}

	function getDocumentTypeFromName(name: string): string {
		if (name.toLowerCase().includes('10-k')) return '10-K';
		if (name.toLowerCase().includes('10-q')) return '10-Q';
		if (name.toLowerCase().includes('8-k')) return '8-K';
		if (name.toLowerCase().includes('mda') || name.toLowerCase().includes('management'))
			return 'MD&A';
		if (name.toLowerCase().includes('risk')) return 'Risk Factors';
		if (name.toLowerCase().includes('business')) return 'Business';
		return 'Document';
	}

	function truncateDocumentName(name: string, maxLength: number = 50): string {
		if (name.length <= maxLength) return name;
		return name.substring(0, maxLength - 3) + '...';
	}
</script>

<div class="space-y-4">
	{#if sources && sources.length > 0}
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<Folder class="text-muted-foreground h-4 w-4" />
				<span class="text-sm font-medium">Source Documents</span>
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

					<div class="hover:bg-muted/50 group rounded-lg border p-3 transition-colors">
						<div class="space-y-2">
							<!-- Document Type Badge -->
							<div class="flex items-start justify-between">
								<Badge variant="secondary" class="text-xs">
									{getDocumentTypeFromName(source.document_name)}
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
								<FileText class="text-muted-foreground mt-0.5 h-4 w-4 flex-shrink-0" />
								<div class="min-w-0 flex-1">
									<p class="text-sm font-medium leading-tight">
										{truncateDocumentName(source.document_name)}
									</p>
								</div>
							</div>

							<!-- Document Actions -->
							<div class="flex items-center justify-between pt-1">
								<p class="text-muted-foreground text-xs">
									ID: {source.id.substring(0, 8)}...
								</p>
								<Button
									variant="ghost"
									size="sm"
									onclick={() => handleSourceClick(source)}
									class="h-6 px-2 text-xs"
								>
									View Document
								</Button>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<Separator />

		<!-- Summary Footer -->
		<div class="text-center">
			<p class="text-muted-foreground text-xs">
				Generated from {sources.length} source {sources.length === 1 ? 'document' : 'documents'}
			</p>
		</div>
	{:else}
		<div class="flex items-center justify-center p-6">
			<div class="text-center">
				<File class="text-muted-foreground mx-auto h-8 w-8" />
				<p class="text-muted-foreground mt-2 text-sm">No source documents available</p>
				<p class="text-muted-foreground text-xs">
					This content may have been generated from other sources
				</p>
			</div>
		</div>
	{/if}
</div>
