<script lang="ts">
	import { ChevronLeft, ExternalLink } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { formatDate, getAnalysisTypeDisplay } from '$lib/utils/filings';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const doc = $derived(data.document);
	const filing = $derived(doc.filing);
	const ticker = $derived(doc.company_ticker);
	const shortHash = $derived(doc.short_hash || data.content_hash.substring(0, 8));
	const typeDisplay = $derived(getAnalysisTypeDisplay(doc.document_type));
</script>

<svelte:head>
	<title>{typeDisplay} - {ticker} - Symbology</title>
	<meta name="description" content="{typeDisplay} from {ticker} SEC filing" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	{#if filing}
		<a
			href="/f/{filing.accession_number}"
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			{ticker} &middot; {filing.form}
			{#if filing.period_of_report}&middot; {formatDate(filing.period_of_report)}{/if}
		</a>
	{:else}
		<a
			href="/c/{ticker}"
			class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
		>
			<ChevronLeft class="h-3 w-3" />
			{ticker}
		</a>
	{/if}
</div>

<!-- Masthead -->
<header style="max-width: 720px;">
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;DOCUMENT &middot;
		{doc.document_type.toUpperCase().replace(/_/g, ' ')}
	</div>
	<h1 class="display" style="margin-bottom: 1rem;">
		{typeDisplay}
	</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 52ch;">
		{doc.title}
	</p>
	<div style="margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
		<span class="tag" style="font-weight: 500; color: var(--ink);">{ticker}</span>
		{#if filing}
			<span class="tag">{filing.form}</span>
			<span class="tag">{formatDate(filing.filing_date)}</span>
		{/if}
		<span class="tag" style="font-family: var(--mono);">{shortHash}</span>
	</div>
</header>

<!-- Article body -->
<article style="margin-top: 5rem; max-width: 720px;">
	{#if doc.content}
		<div class="analysis-body">
			<MarkdownContent content={doc.content} />
		</div>
	{:else}
		<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
			No content available for this document.
		</p>
	{/if}
</article>

<!-- Footer -->
{#if filing}
	<footer
		style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule); max-width: 720px; display: flex; flex-wrap: wrap; gap: 1rem; align-items: center;"
	>
		<span class="meta" style="color: var(--ink-4);">
			Source: {filing.form}
			{#if filing.period_of_report}&middot; Period ending {formatDate(filing.period_of_report)}{/if}
			&middot; Filed {formatDate(filing.filing_date)}
		</span>
		{#if filing.url}
			<a
				href={filing.url}
				target="_blank"
				rel="noopener noreferrer"
				class="meta no-underline"
				style="color: var(--teal-2); margin-left: auto; display: inline-flex; align-items: center; gap: 4px;"
			>
				View on SEC.gov
				<ExternalLink class="h-3 w-3" />
			</a>
		{/if}
	</footer>
{/if}
