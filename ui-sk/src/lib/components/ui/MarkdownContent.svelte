<script lang="ts">
	import { marked } from 'marked';
	import { cn } from '$lib/utils';

	interface Props {
		content: string;
		class?: string;
	}

	const { content, class: className = '' }: Props = $props();

	function renderMarkdown(text: string): string {
		if (!text || text.trim() === '') {
			return '';
		}

		const result = marked.parse(text, {
			breaks: true,
			gfm: true,
			async: false
		});
		return typeof result === 'string' ? result : '';
	}
</script>

<div
	class={cn(
		'prose prose-sm dark:prose-invert max-w-none',
		'prose-zinc dark:prose-zinc',
		'prose-headings:font-semibold prose-headings:tracking-tight',
		'prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg',
		'prose-p:leading-relaxed prose-p:text-muted-foreground',
		'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
		'prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-sm',
		'prose-pre:bg-muted prose-pre:border prose-pre:border-border',
		'prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:px-4 prose-blockquote:py-2 prose-blockquote:rounded-r-md',
		'prose-th:bg-muted prose-th:font-medium',
		'prose-td:border-border prose-th:border-border',
		className
	)}
>
	{@html renderMarkdown(content)}
</div>
