<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { Calendar, Clock, FileText, Eye, Copy, Check } from '@lucide/svelte';
	import type { MockGeneratedContent } from '$lib/mockData';

	let { content }: { content: MockGeneratedContent } = $props();

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

	function renderMarkdown(text: string): string {
		// Simple markdown-to-HTML conversion for demo purposes
		// In production, you'd use a proper markdown parser like marked or remark
		return text
			.replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mb-4">$1</h1>')
			.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-semibold mb-3">$1</h2>')
			.replace(/^### (.*$)/gim, '<h3 class="text-xl font-medium mb-2">$1</h3>')
			.replace(/\*\*(.*)\*\*/gim, '<strong class="font-semibold">$1</strong>')
			.replace(/\*(.*)\*/gim, '<em class="italic">$1</em>')
			.replace(/^\- (.*$)/gim, '<li class="ml-4">$1</li>')
			.replace(/\n\n/gim, '</p><p class="mb-4">')
			.replace(/^(?!<[h|l])/gim, '<p class="mb-4">')
			.replace(/\n/gim, '<br>');
	}
</script>

<div class="space-y-6">
	<!-- Content Metadata -->
	<div class="flex flex-col space-y-3 sm:flex-row sm:items-start sm:justify-between sm:space-y-0">
		<div class="space-y-2">
			{#if content.document_type}
				<Badge variant="secondary" class="text-sm">
					<FileText class="mr-1 h-3 w-3" />
					{content.document_type}
				</Badge>
			{/if}
			<Badge variant="outline" class="text-sm">
				{content.source_type.replace('_', ' ').toUpperCase()}
			</Badge>
		</div>

		<div class="text-muted-foreground flex flex-col space-y-2 text-sm sm:text-right">
			<div class="flex items-center">
				<Calendar class="mr-2 h-4 w-4" />
				Generated {formatDate(content.created_at)}
			</div>
			{#if content.total_duration}
				<div class="flex items-center">
					<Clock class="mr-2 h-4 w-4" />
					Completed in {formatDuration(content.total_duration)}
				</div>
			{/if}
		</div>
	</div>

	<Separator />

	<!-- Summary Section -->
	{#if content.summary}
		<div class="bg-muted/50 rounded-lg border p-4">
			<h3 class="mb-2 font-medium">Summary</h3>
			<p class="text-muted-foreground text-sm">{content.summary}</p>
		</div>
	{/if}

	<!-- Content Section -->
	{#if content.content}
		<div class="space-y-4">
			<div class="flex items-center justify-between">
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
			</div>

			<div class="prose prose-sm dark:prose-invert max-w-none">
				{@html renderMarkdown(content.content)}
			</div>
		</div>
	{:else}
		<div class="flex items-center justify-center rounded-lg border border-dashed p-8">
			<div class="text-center">
				<Eye class="text-muted-foreground mx-auto h-8 w-8" />
				<p class="text-muted-foreground mt-2 text-sm">No content available</p>
			</div>
		</div>
	{/if}
</div>

<style>
	:global(.prose h1, .prose h2, .prose h3) {
		color: hsl(var(--foreground));
	}
	:global(.prose p) {
		color: hsl(var(--muted-foreground));
		line-height: 1.6;
	}
	:global(.prose strong) {
		color: hsl(var(--foreground));
	}
	:global(.prose li) {
		color: hsl(var(--muted-foreground));
		list-style-type: disc;
		margin-left: 1rem;
	}
</style>
