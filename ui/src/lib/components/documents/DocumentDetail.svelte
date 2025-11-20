<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { HandCoins } from '@lucide/svelte';
	import MarkdownContent from '../ui/MarkdownContent.svelte';
	import Separator from '../ui/separator/separator.svelte';
	import type { DocumentResponse } from '$lib/generated-api-types';

	interface Props {
		document: DocumentResponse;
	}

	let { document }: Props = $props();

	function estimateTokens(content: string) {
		// Rough estimation: ~4 characters per token for English text
		return Math.ceil(content.length / 4);
	}
</script>

<Card class="h-full w-full">
	<CardHeader>
		<CardTitle class="text-lg">Document Content</CardTitle>
		{#if document.content}
			<div class="flex text-sm text-muted-foreground">
				<HandCoins class="mr-2 h-4 w-4" />
				~{estimateTokens(document.content || '')} tokens
			</div>
		{/if}
		<!-- TODO: add 'Retrieved on ...' -->
	</CardHeader>
	<CardContent>
		<div class="space-y-4">
			<Separator />
			<MarkdownContent content={document.content} />
		</div>
	</CardContent>
</Card>
