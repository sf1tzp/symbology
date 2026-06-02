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
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html renderMarkdown(content)}
</div>

<style>
	:global(.prose p) {
		margin-bottom: 1rem;
		line-height: 1.7;
		color: var(--ink-2);
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
		margin-top: 1.75rem;
		margin-bottom: 0.75rem;
		font-family: var(--serif);
		color: var(--ink);
		font-weight: 500;
		line-height: 1.25;
		letter-spacing: -0.015em;
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
		border-bottom: 1px solid var(--rule);
		padding-bottom: 0.5rem;
	}

	:global(.prose h2) {
		font-size: 1.5rem;
		border-bottom: 1px solid var(--rule);
		padding-bottom: 0.25rem;
	}

	/* Teal accent marker before lower-level headings for a touch of color */
	:global(.prose h3),
	:global(.prose h4) {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
	}
	:global(.prose h3::before),
	:global(.prose h4::before) {
		content: '';
		flex: none;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--teal-2);
		transform: translateY(-2px);
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
		color: var(--ink-3);
	}

	:global(.prose ul),
	:global(.prose ol) {
		margin: 1rem 0;
		padding-left: 1.5rem;
		color: var(--ink-2);
	}

	:global(.prose li) {
		margin: 0.25rem 0;
		line-height: 1.6;
	}

	:global(.prose li::marker) {
		color: var(--teal-2);
	}

	:global(.prose strong) {
		font-weight: 600;
		color: var(--ink);
	}

	:global(.prose em) {
		font-style: italic;
	}

	:global(.prose code) {
		background-color: var(--paper-2);
		padding: 0.125rem 0.3rem;
		border-radius: var(--radius-sm);
		font-family: var(--mono);
		font-size: 0.85em;
		color: var(--ink-2);
		border: 1px solid var(--rule);
	}

	:global(.prose pre) {
		background-color: var(--paper-2);
		padding: 1rem;
		border-radius: var(--radius);
		overflow-x: auto;
		margin: 1rem 0;
		border: 1px solid var(--rule);
	}

	:global(.prose pre code) {
		background: none;
		padding: 0;
		border: none;
		font-size: 0.85rem;
	}

	:global(.prose blockquote) {
		border-left: 3px solid var(--teal-2);
		margin: 1.25rem 0;
		font-style: italic;
		color: var(--ink-2);
		background-color: var(--sage-2);
		padding: 1rem 1.25rem;
		border-radius: 0 8px 8px 0;
	}

	:global(.prose table) {
		border-collapse: collapse;
		width: 100%;
		margin: 1.5rem 0;
		font-family: var(--sans);
		border: 1px solid var(--rule);
		border-radius: var(--radius);
		overflow: hidden;
	}

	:global(.prose th),
	:global(.prose td) {
		border: 1px solid var(--rule);
		padding: 0.625rem 0.75rem;
		text-align: left;
		color: var(--ink-2);
	}

	:global(.prose th) {
		background-color: var(--sage-2);
		font-weight: 600;
		color: var(--ink);
	}

	:global(.prose tr:nth-child(even)) {
		background-color: var(--paper-2);
	}

	:global(.prose hr) {
		border: none;
		border-top: 1px solid var(--rule);
		margin: 2rem 0;
	}

	:global(.prose a) {
		color: var(--teal-2);
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	:global(.prose a:hover) {
		color: var(--teal-2);
		text-decoration: none;
	}
</style>
