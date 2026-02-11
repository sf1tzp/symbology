<script lang="ts">
	import { Separator } from '$lib/components/ui/separator';
	import { Eye } from '@lucide/svelte';
	import type {
		GeneratedContentResponse,
		ModelConfigResponse,
		DocumentResponse
	} from '$lib/api-types';
	import MarkdownContent from '../ui/MarkdownContent.svelte';

	type SourceItem = (DocumentResponse & { source_type: string }) | (GeneratedContentResponse & { source_type: string });

	let { content }: { content: GeneratedContentResponse & { modelConfig?: ModelConfigResponse | null; sources?: SourceItem[] } } =
		$props();

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

{#if content?.content}
	<MarkdownContent content={cleanContent(content.content) || ''} />
{:else}
	<div class="flex justify-center rounded-lg border border-dashed p-8">
		<div class="text-center">
			<Eye class="mx-auto h-8 w-8 text-muted-foreground" />
			<p class="text-sm text-muted-foreground">No content available</p>
		</div>
	</div>
{/if}
