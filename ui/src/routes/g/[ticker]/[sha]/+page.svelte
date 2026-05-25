<script lang="ts">
	import { ChevronLeft, FileText, Bot } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { formatDate, getAnalysisTypeDisplay, cleanContent } from '$lib/utils/filings';
	import type { DocumentResponse, GeneratedContentResponse } from '$lib/api-types';
	import type { PageData } from './$types';
	import { titleCase } from 'title-case';

	let { data }: { data: PageData } = $props();

	const content = $derived(data.content);
	const company = $derived(data.company);
	const modelConfig = $derived(content?.modelConfig ?? null);
	const sources = $derived(content?.sources ?? []);

	const companyName = $derived(company?.display_name || company?.name || data.ticker);
	const typeDisplay = $derived(
		content?.document_type ? getAnalysisTypeDisplay(content.document_type) : null
	);
	const contentTitle = $derived(typeDisplay ? `${typeDisplay} Analysis` : 'Generated Analysis');
	const cleanedContent = $derived(cleanContent(content?.content ?? undefined));

	function formatDuration(duration: number | null): string {
		if (!duration) return 'N/A';
		if (duration < 60) return `${duration.toFixed(1)}s`;
		const minutes = Math.floor(duration / 60);
		const seconds = Math.floor(duration % 60);
		return `${minutes}m ${seconds}s`;
	}

	function getSourceName(source: DocumentResponse | GeneratedContentResponse): string {
		if ('title' in source) {
			return (source as DocumentResponse).title;
		}
		const gc = source as GeneratedContentResponse;
		return gc.description ? titleCase(gc.description.replace(/_/g, ' ')) : 'Generated Content';
	}

	function getSourceHref(source: DocumentResponse | GeneratedContentResponse): string | null {
		if ('title' in source) {
			const doc = source as DocumentResponse;
			if (doc.filing?.accession_number && (doc.short_hash || doc.content_hash)) {
				return `/d/${doc.filing.accession_number}/${doc.short_hash || doc.content_hash?.substring(0, 12)}`;
			}
			return null;
		}
		const gc = source as GeneratedContentResponse;
		const hash = gc.short_hash || gc.content_hash?.substring(0, 12);
		return hash ? `/g/${data.ticker}/${hash}` : null;
	}

	function isDocument(source: DocumentResponse | GeneratedContentResponse): boolean {
		return 'title' in source;
	}
</script>

<svelte:head>
	<title>{contentTitle} - {companyName} - Symbology</title>
	<meta name="description" content="{contentTitle} for {companyName}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/c/{data.ticker}"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		{companyName}
	</a>
</div>

<!-- Masthead -->
<header>
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;CHANGE ANALYSIS
		{#if typeDisplay}&middot; {typeDisplay.toUpperCase()}{/if}
		{#if content?.form_type}&middot; {content.form_type.toUpperCase()}{/if}
	</div>
	<h1 class="display" style="margin-bottom: 1rem; max-width: 720px;">
		{contentTitle}
	</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 62ch;">
		AI-generated synthesis for {companyName}{#if content?.form_type}
			based on {content.form_type} filings{/if}. Every claim references the source document it came
		from.
	</p>
	<div style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
		{#if content?.form_type}
			<span class="tag">{content.form_type}</span>
		{/if}
		{#if sources.length > 0}
			<span class="tag">{sources.length} source{sources.length !== 1 ? 's' : ''}</span>
		{/if}
		{#if content?.content_hash}
			<span class="tag" style="font-family: var(--mono);"
				>{content.short_hash || content.content_hash.substring(0, 12)}</span
			>
		{/if}
		<span class="meta" style="margin-left: auto; color: var(--ink-4);">
			Generated {formatDate(content.created_at)}
			{#if modelConfig}&middot; {modelConfig.model}{/if}
		</span>
	</div>
</header>

<!-- Two-column article -->
<div class="article-grid" style="margin-top: 5rem;">
	<!-- Sticky sidebar -->
	<aside class="content-sidebar">
		<h3 class="sub" style="margin-bottom: 1rem;">Generation</h3>
		<div style="display: flex; flex-direction: column; gap: 0.75rem;">
			{#if modelConfig}
				<div>
					<div class="meta" style="color: var(--ink-4);">Model</div>
					<div class="meta" style="color: var(--ink-2); margin-top: 2px;">{modelConfig.model}</div>
				</div>
			{/if}
			{#if content?.input_tokens || content?.output_tokens}
				<div>
					<div class="meta" style="color: var(--ink-4);">Tokens</div>
					<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
						{#if content.input_tokens}{content.input_tokens.toLocaleString()} in{/if}
						{#if content.input_tokens && content.output_tokens}
							/
						{/if}
						{#if content.output_tokens}{content.output_tokens.toLocaleString()} out{/if}
					</div>
				</div>
			{/if}
			{#if content?.total_duration}
				<div>
					<div class="meta" style="color: var(--ink-4);">Duration</div>
					<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
						{formatDuration(content.total_duration)}
					</div>
				</div>
			{/if}
			<div>
				<div class="meta" style="color: var(--ink-4);">Generated</div>
				<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
					{formatDate(content.created_at)}
				</div>
			</div>
		</div>

		{#if sources.length > 0}
			<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.75rem 0;" />
			<h3 class="sub" style="margin-bottom: 1rem;">Sources</h3>
			<div style="display: flex; flex-direction: column; gap: 0.75rem;">
				{#each sources as source (source.id)}
					{@const href = getSourceHref(source)}
					{#if href}
						<a {href} class="sidebar-source">
							<div style="display: flex; align-items: center; gap: 6px;">
								{#if isDocument(source)}
									<FileText class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								{:else}
									<Bot class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								{/if}
								<span style="font-size: 13px; color: var(--ink);">
									{getSourceName(source)}
								</span>
							</div>
							{#if source.document_type}
								<div class="meta" style="color: var(--ink-4); margin-top: 2px; padding-left: 18px;">
									{getAnalysisTypeDisplay(source.document_type)}
								</div>
							{/if}
						</a>
					{:else}
						<div>
							<div style="display: flex; align-items: center; gap: 6px;">
								{#if isDocument(source)}
									<FileText class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								{:else}
									<Bot class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								{/if}
								<span style="font-size: 13px; color: var(--ink-3);">
									{getSourceName(source)}
								</span>
							</div>
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</aside>

	<!-- Article body -->
	<article>
		{#if cleanedContent}
			<div class="analysis-body">
				<MarkdownContent content={cleanedContent} />
			</div>
		{:else}
			<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
				No content available.
			</p>
		{/if}
	</article>
</div>

<!-- Footer -->
<footer style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule);">
	<span class="meta" style="color: var(--ink-4);">
		Generated from {content?.source_type === 'documents'
			? 'source documents'
			: content?.source_type === 'generated_content'
				? 'prior analyses'
				: 'source materials'}
		{#if modelConfig}&middot; {modelConfig.model}{/if}
		{#if content?.content_hash}&middot; {content.short_hash ||
				content.content_hash.substring(0, 12)}{/if}
	</span>
</footer>

<style>
	.article-grid {
		display: grid;
		grid-template-columns: 220px 1fr;
		gap: 80px;
		align-items: start;
	}
	@media (max-width: 768px) {
		.article-grid {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
	}

	.content-sidebar {
		position: sticky;
		top: 100px;
		align-self: start;
	}

	.sidebar-source {
		text-decoration: none;
		color: inherit;
		display: block;
		padding: 6px 0;
		transition: color 0.1s;
	}
	.sidebar-source:hover span {
		color: var(--teal-2);
	}
</style>
