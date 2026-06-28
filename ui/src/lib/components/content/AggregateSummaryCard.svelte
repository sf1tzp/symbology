<script lang="ts">
	import type { GeneratedContentResponse } from '$lib/api-types';
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
		if (cleaned.length <= 180) return cleaned;
		return cleaned.substring(0, 180) + '...';
	}

	function handleClick(summary: GeneratedContentResponse) {
		const hash = summary.short_hash || summary.content_hash?.substring(0, 12);
		if (hash) {
			goto(`/g/${ticker}/${hash}`);
		}
	}

	function getCardKind(summary: GeneratedContentResponse): string {
		const docType = summary.description || summary.document_type || '';
		const lower = docType.toLowerCase();
		if (lower.includes('risk')) return 'warn';
		if (lower.includes('control') || lower.includes('procedure')) return 'down';
		return '';
	}
</script>

{#if summaries.length > 0}
	<div class={summaries.length >= 3 ? 'grid-3' : 'grid-2'}>
		{#each summaries as summary (summary.id)}
			<button
				class="change-card {getCardKind(summary)}"
				onclick={() => handleClick(summary)}
				style="cursor: pointer; text-align: left; background: none;"
			>
				<div class="flex-between">
					<span class="eyebrow" style="font-size: 10px;">
						{getAnalysisTypeDisplay(summary.description || summary.document_type || 'Synthesis')}
						{#if summary.form_type}
							&middot; {summary.form_type}
						{/if}
					</span>
					<span class="meta" style="color: var(--ink-4);">{formatDate(summary.created_at)}</span>
				</div>
				{#if summary.summary}
					<p
						style="font-family: var(--serif); font-size: 15px; line-height: 1.5; color: var(--ink-2); margin: 0.25rem 0;"
					>
						{getPreview(summary.summary)}
					</p>
				{/if}
				<div class="meta" style="color: var(--teal-2); margin-top: auto;">
					Read full analysis &rarr;
				</div>
			</button>
		{/each}
	</div>
{/if}
