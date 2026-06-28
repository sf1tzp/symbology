<script lang="ts">
	import { ChevronLeft, FileText, Bot, GitCompare } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import { formatDate, getAnalysisTypeDisplay, cleanContent } from '$lib/utils/filings';
	import { stageMeta as stageMetaFor } from '$lib/utils/synthesis';
	import type { DocumentResponse, GeneratedContentResponse } from '$lib/api-types';
	import type { PageData } from './$types';
	import { titleCase } from 'title-case';

	let { data }: { data: PageData } = $props();

	const content = $derived(data.content);
	const scope = $derived(data.scope);
	const modelConfig = $derived(content?.modelConfig ?? null);
	const sources = $derived(content?.sources ?? []);
	// Topic-diff sources: `diffView` carries the raw token ops + filing refs for the
	// side-by-side DiffView; `diffSources` are its flattened halves for the sidebar.
	const diffView = $derived(content?.diffView ?? null);
	const diffSources = $derived(diffView?.sides ?? []);
	const systemPrompt = $derived(content?.systemPrompt ?? null);
	const userPrompt = $derived(content?.userPrompt ?? null);

	const scopeName = $derived(scope?.label ?? 'Symbology');
	const typeDisplay = $derived(
		content?.document_type ? getAnalysisTypeDisplay(content.document_type) : null
	);

	// Human framing per content stage — the /s/ viewer serves every kind of
	// synthesis (page intros, overviews, change syntheses, summaries), so the
	// masthead adapts rather than hard-coding "Change Synthesis".
	const stageMeta = $derived(stageMetaFor(content?.content_stage));
	const isTopicDiff = $derived(content?.content_stage === 'topic_diff_summary');
	const contentTitle = $derived(typeDisplay ? `${typeDisplay} ${stageMeta.noun}` : stageMeta.noun);
	const lede = $derived(
		isTopicDiff
			? `AI synthesis of how this disclosure changed between two consecutive ${content?.form_type ?? ''} filings for ${scopeName}, generated from the prior- and current-period text below.`
			: `AI-generated ${stageMeta.noun.toLowerCase()} for ${scopeName}${content?.form_type ? ` based on ${content.form_type} filings` : ''}. Built from the sources listed alongside.`
	);
	const cleanedContent = $derived(cleanContent(content?.content ?? undefined));

	// Total source count across association-based sources and diff halves, for the tag.
	const sourceCount = $derived(sources.length + diffSources.length);

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
		return hash ? `/s/${hash}` : null;
	}

	function isDocument(source: DocumentResponse | GeneratedContentResponse): boolean {
		return 'title' in source;
	}
</script>

<svelte:head>
	<title>{contentTitle} - {scopeName} - Symbology</title>
	<meta name="description" content="{contentTitle} for {scopeName}" />
</svelte:head>

<!-- Back link (omitted when the content has no navigable scope) -->
{#if scope?.href}
	<div style="margin-bottom: 3rem;">
		<a
			href={scope.href}
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			{scopeName}
		</a>
	</div>
{/if}

<!-- Masthead -->
<header>
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{stageMeta.eyebrow.toUpperCase()}
		{#if typeDisplay}&middot; {typeDisplay.toUpperCase()}{/if}
		{#if content?.form_type}&middot; {content.form_type.toUpperCase()}{/if}
	</div>
	<h1 class="display" style="margin-bottom: 1rem; max-width: 720px;">
		{contentTitle}
	</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 62ch;">
		{lede}
	</p>
	<div style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
		{#if content?.form_type}
			<span class="tag">{content.form_type}</span>
		{/if}
		{#if sourceCount > 0}
			<span class="tag">{sourceCount} source{sourceCount !== 1 ? 's' : ''}</span>
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
				{#if modelConfig.temperature != null || modelConfig.max_tokens != null}
					<div>
						<div class="meta" style="color: var(--ink-4);">Config</div>
						<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
							{#if modelConfig.temperature != null}temp {modelConfig.temperature}{/if}
							{#if modelConfig.temperature != null && modelConfig.max_tokens != null}
								&middot;
							{/if}
							{#if modelConfig.max_tokens != null}{modelConfig.max_tokens.toLocaleString()} max{/if}
						</div>
					</div>
				{/if}
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

		{#if sources.length > 0 || diffSources.length > 0}
			<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.75rem 0;" />
			<h3 class="sub" style="margin-bottom: 1rem;">Sources</h3>
			<div style="display: flex; flex-direction: column; gap: 0.75rem;">
				{#each diffSources as side (side.period)}
					{#if side.href}
						<a href={side.href} class="sidebar-source">
							<div style="display: flex; align-items: center; gap: 6px;">
								<GitCompare class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								<span style="font-size: 13px; color: var(--ink);">{side.label}</span>
							</div>
							{#if side.filingForm || side.filingDate}
								<div class="meta" style="color: var(--ink-4); margin-top: 2px; padding-left: 18px;">
									{side.filingForm ?? ''}{#if side.filingForm && side.filingDate}
										&middot;
									{/if}{side.filingDate ? formatDate(side.filingDate) : ''}
								</div>
							{/if}
						</a>
					{:else}
						<div>
							<div style="display: flex; align-items: center; gap: 6px;">
								<GitCompare class="h-3 w-3" style="color: var(--ink-4); flex-shrink: 0;" />
								<span style="font-size: 13px; color: var(--ink-3);">{side.label}</span>
							</div>
						</div>
					{/if}
				{/each}
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

		<!-- Diff source halves: the two texts a topic-diff synthesis compared, shown
		     as a highlighted side-by-side diff via the shared DiffView. -->
		{#if diffView}
			<section style="margin-top: 3.5rem;">
				<h2
					class="sub"
					style="margin-bottom: 1.25rem; display: flex; align-items: center; gap: 8px;"
				>
					<GitCompare class="h-3.5 w-3.5" style="color: var(--ink-4);" />
					Source comparison
				</h2>
				<DiffView
					topic={diffView.topic}
					leftFiling={diffView.leftFiling}
					rightFiling={diffView.rightFiling}
				/>
			</section>
		{/if}

		<!-- Prompt(s) used for this generation. -->
		{#if systemPrompt || userPrompt}
			<section style="margin-top: 3.5rem;">
				<h2 class="sub" style="margin-bottom: 1.25rem;">Prompt</h2>
				{#if systemPrompt}
					<details class="prompt-block">
						<summary>
							<span class="prompt-role">System</span>
							<span class="meta" style="color: var(--ink-3);">{systemPrompt.name}</span>
						</summary>
						<pre class="prompt-content">{systemPrompt.content}</pre>
					</details>
				{/if}
				{#if userPrompt}
					<details class="prompt-block">
						<summary>
							<span class="prompt-role">User</span>
							<span class="meta" style="color: var(--ink-3);">{userPrompt.name}</span>
						</summary>
						<pre class="prompt-content">{userPrompt.content}</pre>
					</details>
				{/if}
			</section>
		{/if}
	</article>
</div>

<!-- Footer -->
<footer style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule);">
	<span class="meta" style="color: var(--ink-4);">
		Generated from {content?.source_type === 'documents'
			? 'source documents'
			: content?.source_type === 'generated_content'
				? 'prior syntheses'
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
	.content-sidebar {
		position: sticky;
		top: 100px;
		align-self: start;
	}

	@media (max-width: 768px) {
		.article-grid {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
		/* Single column: show the article first, then the generation metadata
		   below it. The sidebar must not stay sticky here or it floats over the
		   content as the reader scrolls. */
		article {
			order: 1;
		}
		.content-sidebar {
			order: 2;
			position: static;
			top: auto;
			padding-top: 1.75rem;
			border-top: 1px solid var(--rule);
		}
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

	.prompt-block {
		border: 1px solid var(--rule);
		border-radius: 6px;
		margin-bottom: 0.75rem;
		overflow: hidden;
	}
	.prompt-block summary {
		cursor: pointer;
		padding: 0.75rem 1rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		user-select: none;
	}
	.prompt-block summary:hover {
		background: var(--paper-2, transparent);
	}
	.prompt-role {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--teal-2);
		font-weight: 600;
	}
	.prompt-content {
		margin: 0;
		padding: 1rem;
		border-top: 1px solid var(--rule);
		font-family: var(--mono);
		font-size: 12.5px;
		line-height: 1.6;
		color: var(--ink-2);
		white-space: pre-wrap;
		word-break: break-word;
		max-height: 520px;
		overflow-y: auto;
	}
</style>
