<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
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
		<CardDescription>
			{#if document.content}
				<div class="flex items-center">
					<HandCoins class="mr-2 h-4 w-4" />
					~{estimateTokens(document.content || '')} tokens
				</div>
			{/if}
			<!-- TODO: add 'Retrieved on ...' -->
		</CardDescription>
	</CardHeader>
	<CardContent>
		<div class="space-y-4">
			<Separator />
			<div
				class="bg-muted/30 mt-3 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-md p-4 text-sm"
			>
				<MarkdownContent content={document.content} />
			</div>
			<Separator />
		</div>
	</CardContent>
</Card>
