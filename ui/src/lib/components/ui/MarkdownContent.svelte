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
		const html = typeof result === 'string' ? result : '';
		// Wrap tables so wide ones scroll horizontally instead of overflowing the page.
		// marked emits bare <table>…</table>, so a string swap is safe here.
		const withTables = html
			.replaceAll('<table>', '<div class="table-scroll"><table>')
			.replaceAll('</table>', '</table></div>');
		return sectionizeHeadings(withTables);
	}

	// Wrap each top-level heading and the content that follows it (up to the next
	// heading) in a <section>. That gives every heading its own containing block,
	// so on mobile it can stick within just its own section instead of all the
	// headings sharing .prose and piling up at the top of the viewport. marked
	// emits headings only at the top level and escapes HTML inside code blocks, so
	// splitting on heading open-tags is safe.
	function sectionizeHeadings(html: string): string {
		return html
			.split(/(?=<h[1-6][\s>])/i)
			.map((part) =>
				/^<h[1-6][\s>]/i.test(part) ? `<section class="md-section">${part}</section>` : part
			)
			.join('');
	}
</script>

<div class="prose prose-gray dark:prose-invert max-w-none {className}">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html renderMarkdown(content)}
</div>

<style>
	/* Long unbreakable tokens (URLs, run-together words) wrap instead of overflowing.
	   overflow-wrap is inherited, so this covers all prose descendants. */
	:global(.prose) {
		overflow-wrap: break-word;
		min-width: 0;
	}

	/* Horizontal scroll container for wide tables (see renderMarkdown). */
	:global(.prose .table-scroll) {
		margin: 1.5rem 0;
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}

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

	/* Only the very first heading of the content drops its top margin. Headings are
	   now each wrapped in their own .md-section (see sectionizeHeadings), so a bare
	   :first-child would match every heading and collapse the inter-section gap. */
	:global(.prose > .md-section:first-child > h1),
	:global(.prose > .md-section:first-child > h2),
	:global(.prose > .md-section:first-child > h3),
	:global(.prose > .md-section:first-child > h4),
	:global(.prose > .md-section:first-child > h5),
	:global(.prose > .md-section:first-child > h6) {
		margin-top: 0;
	}

	/* Mobile-only sticky section headings, mirroring the SectionHead affordance.
	   Each heading pins within its own .md-section, so as you scroll the nearest
	   heading stays near the top of the viewport for orientation. The opaque
	   background + bottom padding (replacing the bottom margin) cover content
	   sliding underneath.

	   top is --md-heading-sticky-top, which a sticky SectionHead in the same
	   container publishes as its bar height (see SectionHead) so these headings
	   stack *beneath* it rather than overlapping. It defaults to 0 when there's no
	   sticky header above — the top nav is hidden off the home screen on mobile, so
	   that pins flush to the viewport top. */
	@media (max-width: 767.98px) {
		:global(.prose .md-section > h1),
		:global(.prose .md-section > h2),
		:global(.prose .md-section > h3),
		:global(.prose .md-section > h4),
		:global(.prose .md-section > h5),
		:global(.prose .md-section > h6) {
			position: sticky;
			top: var(--md-heading-sticky-top, 0px);
			z-index: 20;
			/* background: var(--background); */
			margin-bottom: 0;
			padding-bottom: 0.75rem;
			background-color: color-mix(in srgb, var(--background) 80%, transparent);
			backdrop-filter: blur(12px);
			/* bg-background/90 backdrop-blur-md */
		}
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
	@media (min-width: 767.98px) {
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
		margin: 0;
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
