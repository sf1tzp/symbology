<script lang="ts">
	import type { GeneratedContentResponse } from '$lib/api-types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Sparkles } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { getAnalysisTypeDisplay, formatDate, cleanContent } from '$lib/utils/filings';

	interface Props {
		summaries: GeneratedContentResponse[];
		ticker: string;
	}

	let { summaries, ticker }: Props = $props();

	function getPreview(content: string | null | undefined): string {
		if (!content) return '';
		const cleaned = cleanContent(content) ?? '';
		if (cleaned.length <= 200) return cleaned;
		return cleaned.substring(0, 200) + '...';
	}

	function handleClick(summary: GeneratedContentResponse) {
		const hash = summary.short_hash || summary.content_hash?.substring(0, 12);
		if (hash) {
			goto(`/g/${ticker}/${hash}`);
		}
	}
</script>

{#if summaries.length > 0}
	<div class="space-y-4">
		<div class="flex items-center gap-2">
			<Sparkles class="h-5 w-5 text-primary" />
			<h2 class="text-lg font-semibold">Change Analysis Reports</h2>
		</div>
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			{#each summaries as summary (summary.id)}
				<Card
					class="border-primary/20 bg-primary/[0.02] transition-shadow hover:shadow-md"
					onclick={() => handleClick(summary)}
				>
					<CardContent class="space-y-2">
						<div class="flex items-start justify-between gap-2">
							<div class="flex items-center gap-2">
								<Badge variant="outline" class="text-xs">
									{getAnalysisTypeDisplay(
										summary.description || summary.document_type || 'Analysis'
									)}
								</Badge>
								{#if summary.form_type}
									<Badge variant="secondary" class="text-[10px]">
										{summary.form_type}
									</Badge>
								{/if}
							</div>
							<span class="shrink-0 text-xs text-muted-foreground">
								{formatDate(summary.created_at)}
							</span>
						</div>
						{#if summary.summary}
							<p class="line-clamp-3 text-sm text-muted-foreground">
								{getPreview(summary.summary)}
							</p>
						{/if}
						<Button variant="ghost" size="sm" class="h-auto p-0 text-xs text-primary">
							Read full analysis →
						</Button>
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
{/if}
