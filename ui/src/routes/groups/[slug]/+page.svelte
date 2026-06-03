<script lang="ts">
	import { ChevronLeft } from '@lucide/svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { formatDate, cleanContent } from '$lib/utils/filings';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const group = $derived(data.group);
	const analyses = $derived(data.analyses || []);
	const frontpageSummary = $derived(data.frontpageSummary);
	const companies = $derived(group?.companies || []);
	const modelConfig = $derived(data.modelConfig ?? null);

	const cleanedSummary = $derived(frontpageSummary ? cleanContent(frontpageSummary) : null);
	const latestAnalysis = $derived(analyses.length > 0 ? analyses[0] : null);
	const cleanedAnalysis = $derived(
		latestAnalysis?.content ? cleanContent(latestAnalysis.content) : null
	);

	function formatDuration(duration: number | null): string {
		if (!duration) return 'N/A';
		if (duration < 60) return `${duration.toFixed(1)}s`;
		const minutes = Math.floor(duration / 60);
		const seconds = Math.floor(duration % 60);
		return `${minutes}m ${seconds}s`;
	}
</script>

<svelte:head>
	<title>{group?.name || data.slug} - Sector - Symbology</title>
	<meta name="description" content="Cross-company analysis for {group?.name || data.slug}" />
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/groups"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		All Sectors
	</a>
</div>

{#if !group}
	<div
		style="border-left: 3px solid var(--danger); padding: 1rem 1.25rem; margin-bottom: 2rem; background: color-mix(in oklch, var(--danger) 8%, var(--paper));"
	>
		<p class="meta" style="color: var(--danger); font-weight: 500;">Sector not found</p>
		<p class="meta" style="margin-top: 4px; color: var(--ink-3);">
			No Sector found for "{data.slug}"
		</p>
	</div>
{:else}
	<!-- Masthead -->
	<header class="grid grid-cols-1 gap-8 md:grid-cols-[1fr_auto] md:items-end">
		<div>
			<div class="eyebrow" style="margin-bottom: 1rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;SECTOR
			</div>
			<h1 class="display" style="margin-bottom: 0.75rem;">
				{group.name}
			</h1>
			{#if group.description}
				<p class="lede" style="color: var(--ink-2); max-width: 52ch;">
					{group.description}
				</p>
			{/if}
		</div>
		<div
			class="grid-2"
			style="padding: 1.5rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); gap: 2rem;"
		>
			<div class="stat">
				<span class="stat-value">{group.member_count}</span>
				<span class="stat-label">Members</span>
			</div>
			<div class="stat">
				<span class="stat-value">{analyses.length}</span>
				<span class="stat-label">Analyses</span>
			</div>
		</div>
	</header>

	<!-- Group Synthesis -->
	{#if cleanedSummary}
		<section class="hairline-section">
			<div class="two-col">
				<div>
					<h3 class="sub" style="margin-bottom: 14px;">Sector Synthesis</h3>
					<p class="meta" style="color: var(--ink-4); line-height: 1.6; max-width: 30ch;">
						Generated from aggregate analyses of every member in the group.
					</p>
				</div>
				<div class="analysis-body">
					<MarkdownContent content={cleanedSummary} />
				</div>
			</div>
		</section>
	{/if}

	<!-- Analysis article with sidebar -->
	{#if cleanedAnalysis}
		<section class="hairline-section">
			<div class="eyebrow" style="margin-bottom: 10px;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;ANALYSIS
			</div>
			<h2 class="section-heading" style="margin-bottom: 2rem;">Cross-company analysis</h2>

			<div class="article-grid">
				<!-- Sticky sidebar -->
				<aside class="content-sidebar">
					<h3 class="sub" style="margin-bottom: 1rem;">Generation</h3>
					<div style="display: flex; flex-direction: column; gap: 0.75rem;">
						{#if modelConfig}
							<div>
								<div class="meta" style="color: var(--ink-4);">Model</div>
								<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
									{modelConfig.model}
								</div>
							</div>
						{/if}
						{#if latestAnalysis?.input_tokens || latestAnalysis?.output_tokens}
							<div>
								<div class="meta" style="color: var(--ink-4);">Tokens</div>
								<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
									{#if latestAnalysis.input_tokens}{latestAnalysis.input_tokens.toLocaleString()}
										in{/if}
									{#if latestAnalysis.input_tokens && latestAnalysis.output_tokens}
										/
									{/if}
									{#if latestAnalysis.output_tokens}{latestAnalysis.output_tokens.toLocaleString()}
										out{/if}
								</div>
							</div>
						{/if}
						{#if latestAnalysis?.total_duration}
							<div>
								<div class="meta" style="color: var(--ink-4);">Duration</div>
								<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
									{formatDuration(latestAnalysis.total_duration)}
								</div>
							</div>
						{/if}
						<div>
							<div class="meta" style="color: var(--ink-4);">Generated</div>
							<div class="meta" style="color: var(--ink-2); margin-top: 2px;">
								{formatDate(latestAnalysis?.created_at ?? '')}
							</div>
						</div>
					</div>

					<!-- Member companies in sidebar -->
					{#if companies.length > 0}
						<hr style="border: none; border-top: 1px solid var(--rule); margin: 1.75rem 0;" />
						<h3 class="sub" style="margin-bottom: 1rem;">Members</h3>
						<div style="display: flex; flex-direction: column; gap: 0.5rem;">
							{#each companies as company (company.id)}
								<a href="/c/{company.ticker}" class="sidebar-member">
									<div style="display: flex; align-items: center; gap: 8px;">
										<span
											class="tag"
											style="font-size: 10px; font-weight: 500; color: var(--ink); padding: 1px 6px;"
											>{company.ticker}</span
										>
										<span style="font-size: 13px; color: var(--ink);">
											{company.display_name || company.name}
										</span>
									</div>
									{#if company.sic_description}
										<div
											class="meta"
											style="color: var(--ink-4); margin-top: 1px; padding-left: 0;"
										>
											{company.sic_description}
										</div>
									{/if}
								</a>
							{/each}
						</div>
					{/if}
				</aside>

				<!-- Article body -->
				<article>
					<div class="analysis-body">
						<MarkdownContent content={cleanedAnalysis} />
					</div>

					<!-- Older analyses -->
					{#if analyses.length > 1}
						{#each analyses.slice(1) as analysis (analysis.id)}
							<div style="margin-top: 3rem; padding-top: 3rem; border-top: 1px solid var(--rule);">
								<div class="meta" style="color: var(--ink-4); margin-bottom: 1.5rem;">
									Generated {formatDate(analysis.created_at)}
								</div>
								{#if analysis.content}
									<div class="analysis-body">
										<MarkdownContent content={cleanContent(analysis.content) || ''} />
									</div>
								{/if}
							</div>
						{/each}
					{/if}
				</article>
			</div>
		</section>
	{:else if !cleanedSummary}
		<section class="hairline-section">
			<div class="eyebrow" style="margin-bottom: 10px;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;ANALYSIS
			</div>
			<h2 class="section-heading" style="margin-bottom: 2rem;">Cross-company analysis</h2>
			<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
				No group analysis available yet. Trigger analysis via the CLI to generate cross-company
				insights.
			</p>
		</section>
	{/if}

	<!-- Footer -->
	{#if latestAnalysis}
		<footer style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule);">
			<span class="meta" style="color: var(--ink-4);">
				Generated from member company analyses
				{#if modelConfig}&middot; {modelConfig.model}{/if}
				{#if latestAnalysis.content_hash}&middot; {latestAnalysis.short_hash ||
						latestAnalysis.content_hash.substring(0, 12)}{/if}
			</span>
		</footer>
	{/if}
{/if}

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

	.sidebar-member {
		text-decoration: none;
		color: inherit;
		display: block;
		padding: 6px 0;
		transition: color 0.1s;
	}
	.sidebar-member:hover span {
		color: var(--teal-2);
	}
</style>
