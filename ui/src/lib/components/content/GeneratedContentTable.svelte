<script lang="ts">
	import type { GeneratedContentSummaryResponse } from '$lib/api-types';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Sparkles } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { getAnalysisTypeDisplay, formatDate } from '$lib/utils/filings';

	interface Props {
		content: GeneratedContentSummaryResponse[];
		ticker: string;
	}

	let { content, ticker }: Props = $props();

	function getContextLabel(gc: GeneratedContentSummaryResponse): string {
		const stage = gc.content_stage;
		const docType = gc.document_type;
		const form = gc.form_type;

		const stageLabels: Record<string, string> = {
			single_summary: 'Single summary',
			aggregate_summary: 'Aggregate summary',
			frontpage_summary: 'Frontpage summary',
			company_group_analysis: 'Group analysis'
		};

		const parts: string[] = [];
		if (stage) {
			parts.push(stageLabels[stage] || stage);
		}
		if (docType) {
			parts.push(`for ${getAnalysisTypeDisplay(docType)}`);
		}
		if (form) {
			parts.push(`of ${form}`);
		}

		if (parts.length > 0) return parts.join(' ');

		// Fallback to description
		if (gc.description) return getAnalysisTypeDisplay(gc.description);
		return 'Generated content';
	}

	function getStageBadgeVariant(
		stage: string | null
	): 'default' | 'secondary' | 'outline' | 'destructive' {
		switch (stage) {
			case 'aggregate_summary':
				return 'default';
			case 'frontpage_summary':
				return 'default';
			case 'single_summary':
				return 'secondary';
			case 'company_group_analysis':
				return 'outline';
			default:
				return 'secondary';
		}
	}

	function handleRowClick(gc: GeneratedContentSummaryResponse) {
		const hash = gc.short_hash || gc.content_hash?.substring(0, 12);
		if (hash) {
			goto(`/g/${ticker}/${hash}`);
		}
	}
</script>

{#if content.length > 0}
	<Card>
		<CardHeader>
			<CardTitle class="flex items-center gap-2 text-base">
				<Sparkles class="h-4 w-4 text-primary" />
				All Generated Content
			</CardTitle>
		</CardHeader>
		<CardContent>
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="border-b">
							<th class="py-2 pr-4 text-left text-xs font-medium text-muted-foreground">Content</th>
							<th class="px-2 py-2 text-left text-xs font-medium text-muted-foreground">Stage</th>
							<th class="px-2 py-2 text-left text-xs font-medium text-muted-foreground">Form</th>
							<th class="px-2 py-2 text-right text-xs font-medium text-muted-foreground">Created</th
							>
						</tr>
					</thead>
					<tbody>
						{#each content as gc (gc.id)}
							<tr
								class="cursor-pointer border-b border-border/50 transition-colors hover:bg-muted/50"
								onclick={() => handleRowClick(gc)}
							>
								<td class="max-w-md py-2 pr-4">
									<div class="text-sm font-medium">{getContextLabel(gc)}</div>
									{#if gc.summary}
										<div class="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
											{gc.summary}
										</div>
									{/if}
								</td>
								<td class="px-2 py-2">
									{#if gc.content_stage}
										<Badge variant={getStageBadgeVariant(gc.content_stage)} class="text-[10px]">
											{gc.content_stage.replace(/_/g, ' ')}
										</Badge>
									{/if}
								</td>
								<td class="px-2 py-2">
									{#if gc.form_type}
										<Badge variant="secondary" class="text-[10px]">
											{gc.form_type}
										</Badge>
									{/if}
								</td>
								<td class="px-2 py-2 text-right text-xs whitespace-nowrap text-muted-foreground">
									{formatDate(gc.created_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</CardContent>
	</Card>
{/if}
