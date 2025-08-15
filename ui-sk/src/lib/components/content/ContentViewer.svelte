<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { Calendar, Clock, FileText, Eye, Copy, Check } from '@lucide/svelte';
	import type { GeneratedContentResponse } from '$lib/generated-api-types';
	import MarkdownContent from '../ui/MarkdownContent.svelte';
	import Card from '../ui/card/card.svelte';
	import CardHeader from '../ui/card/card-header.svelte';
	import CardContent from '../ui/card/card-content.svelte';
	import CardTitle from '../ui/card/card-content.svelte';

	let { content }: { content: GeneratedContentResponse & { modelConfig?: any; sources?: any[] } } =
		$props();

	const dispatch = createEventDispatcher();

	let copied = $state(false);

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

	async function copyContent() {
		if (content.content) {
			try {
				await navigator.clipboard.writeText(content.content);
				copied = true;
				setTimeout(() => (copied = false), 2000);
			} catch (err) {
				console.error('Failed to copy content:', err);
			}
		}
	}

	function estimateTokens(content: string) {
		// Rough estimation: ~4 characters per token for English text
		return Math.ceil(content.length / 4);
	}

	/**
	 * Clean content by removing <think> tags and internal reasoning patterns
	 */
	export function cleanContent(content: string | undefined): string | undefined {
		if (!content) return undefined;

		// Remove <think>...</think> blocks and any content before them
		let cleaned = content.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

		// Also handle cases where there might be thinking content without tags
		cleaned = cleaned.replace(
			/^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
			''
		);

		// Trim any remaining whitespace
		cleaned = cleaned.trim();

		return cleaned || undefined;
	}
</script>

<div class="space-y-6">
	<!-- Content Metadata -->
	<!-- <div
		class="flex flex-col space-y-3 sm:flex-row sm:items-start sm:justify-between sm:space-y-0"
	></div> -->

	<Separator />

	<!-- Summary Section -->
	<!-- {#if content.summary}
		<div class="bg-muted/50 rounded-lg border p-4">
			<h3 class="mb-2 font-medium">Summary</h3>
			<p class="text-muted-foreground text-sm">{content.summary}</p>
		</div>
	{/if} -->

	<!-- Content Section -->
	{#if content.content}
		<div class="space-y-4">
			<!-- <div class="flex items-center justify-between">
				<h3 class="font-medium">Generated Content</h3>
				<div class="flex items-center space-x-2">
					<Button
						variant="ghost"
						size="sm"
						onclick={copyContent}
						class="text-muted-foreground hover:text-foreground"
					>
						{#if copied}
							<Check class="h-4 w-4" />
						{:else}
							<Copy class="h-4 w-4" />
						{/if}
						<span class="ml-1">{copied ? 'Copied!' : 'Copy'}</span>
					</Button>
				</div>
			</div> -->

			<MarkdownContent content={cleanContent(content.content || '')} />
		</div>
	{:else}
		<div class="flex items-center justify-center rounded-lg border border-dashed p-8">
			<div class="text-center">
				<Eye class="mx-auto h-8 w-8 text-muted-foreground" />
				<p class="mt-2 text-sm text-muted-foreground">No content available</p>
			</div>
		</div>
	{/if}
</div>

<style>
</style>
