<script lang="ts">
	import { marked } from 'marked';

	const { content, class: className = '' } = $props<{
		content: string;
		class?: string;
	}>();

	function renderMarkdown(text: string): string {
		const result = marked.parse(text, {
			breaks: true,
			gfm: true,
			async: false
		});
		return typeof result === 'string' ? result : '';
	}
</script>

<div class="prose prose-gray dark:prose-invert max-w-none {className}">
	{@html renderMarkdown(content)}
</div>

<style>
	:global(.prose p) {
		margin-bottom: 1rem;
		line-height: 1.7;
		color: hsl(var(--foreground));
	}

	:global(.prose p:last-child) {
		margin-bottom: 0;
	}

	:global(.prose h1),
	:global(.prose h2),
	:global(.prose h3),
	:global(.prose h4),
	:global(.prose h5),
	:global(.prose h6) {
		margin-top: 1.5rem;
		margin-bottom: 0.75rem;
		color: hsl(var(--foreground));
		font-weight: 600;
		line-height: 1.3;
	}

	:global(.prose h1:first-child),
	:global(.prose h2:first-child),
	:global(.prose h3:first-child),
	:global(.prose h4:first-child),
	:global(.prose h5:first-child),
	:global(.prose h6:first-child) {
		margin-top: 0;
	}

	:global(.prose h1) {
		font-size: 1.875rem;
		border-bottom: 2px solid hsl(var(--border));
		padding-bottom: 0.5rem;
	}

	:global(.prose h2) {
		font-size: 1.5rem;
		border-bottom: 1px solid hsl(var(--border));
		padding-bottom: 0.25rem;
	}

	:global(.prose h3) {
		font-size: 1.25rem;
	}

	:global(.prose h4) {
		font-size: 1.125rem;
	}

	:global(.prose h5) {
		font-size: 1rem;
	}

	:global(.prose h6) {
		font-size: 0.875rem;
		color: hsl(var(--muted-foreground));
	}

	:global(.prose ul),
	:global(.prose ol) {
		margin: 1rem 0;
		padding-left: 1.5rem;
	}

	:global(.prose li) {
		margin: 0.25rem 0;
		line-height: 1.6;
	}

	:global(.prose strong) {
		font-weight: 600;
		color: hsl(var(--foreground));
	}

	:global(.prose em) {
		font-style: italic;
	}

	:global(.prose code) {
		background-color: hsl(var(--muted));
		padding: 0.125rem 0.25rem;
		border-radius: calc(var(--radius) - 2px);
		font-family:
			ui-monospace, SFMono-Regular, 'SF Mono', Monaco, Consolas, 'Liberation Mono', 'Courier New',
			monospace;
		font-size: 0.875em;
		border: 1px solid hsl(var(--border));
	}

	:global(.prose pre) {
		background-color: hsl(var(--muted));
		padding: 1rem;
		border-radius: var(--radius);
		overflow-x: auto;
		margin: 1rem 0;
		border: 1px solid hsl(var(--border));
	}

	:global(.prose pre code) {
		background: none;
		padding: 0;
		border: none;
		font-size: 0.875rem;
	}

	:global(.prose blockquote) {
		border-left: 4px solid hsl(var(--primary));
		padding-left: 1rem;
		margin: 1rem 0;
		font-style: italic;
		color: hsl(var(--muted-foreground));
		background-color: hsl(var(--muted) / 0.5);
		padding: 1rem;
		border-radius: var(--radius);
	}

	:global(.prose table) {
		border-collapse: collapse;
		width: 100%;
		margin: 1.5rem 0;
		border: 1px solid hsl(var(--border));
		border-radius: var(--radius);
		overflow: hidden;
	}

	:global(.prose th),
	:global(.prose td) {
		border: 1px solid hsl(var(--border));
		padding: 0.75rem;
		text-align: left;
	}

	:global(.prose th) {
		background-color: hsl(var(--muted));
		font-weight: 600;
		color: hsl(var(--foreground));
	}

	:global(.prose tr:nth-child(even)) {
		background-color: hsl(var(--muted) / 0.3);
	}

	:global(.prose hr) {
		border: none;
		border-top: 1px solid hsl(var(--border));
		margin: 2rem 0;
	}

	:global(.prose a) {
		color: hsl(var(--primary));
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	:global(.prose a:hover) {
		color: hsl(var(--primary));
		text-decoration: none;
	}
</style>
