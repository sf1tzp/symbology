<script lang="ts">
	import { cleanContent } from '$lib/utils/filings';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const groups = $derived(data.groups || []);

	function truncateSummary(text: string | null | undefined, maxLength: number = 200): string {
		if (!text) return '';
		const cleaned = cleanContent(text) ?? '';
		if (cleaned.length <= maxLength) return cleaned;
		return cleaned.substring(0, maxLength).replace(/\s+\S*$/, '') + '…';
	}
</script>

<svelte:head>
	<title>Groups - Symbology</title>
	<meta name="description" content="Cross-company synthesis groups on Symbology" />
</svelte:head>

<!-- Masthead -->
<header>
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;SECTORS &middot; CROSS-COMPANY
		ANALYSIS
	</div>
	<h1 class="display" style="margin-bottom: 1rem;">
		{groups.length} sector{groups.length !== 1 ? 's' : ''}.<br />
		<em>One synthesized view.</em>
	</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 56ch;">
		A Sector bundles a handful of comparable companies. Symbology generates a cross-company analysis
		from their aggregate filings — what's true across the sector, what one player is doing
		differently, and what's quietly changed since last quarter.
	</p>
</header>

{#if groups.length > 0}
	<section class="hairline-section" style="margin-top: 5rem;">
		<div class="grid-2" style="gap: 1.5rem;">
			{#each groups as group (group.id)}
				<a href="/groups/{group.slug}" class="group-card">
					<div class="flex-between" style="margin-bottom: 1.25rem;">
						<h3
							style="font-family: var(--serif); font-size: 1.75rem; font-weight: 400; letter-spacing: -0.02em; color: var(--ink); margin: 0;"
						>
							{group.name}
						</h3>
						<span class="tag" style="flex-shrink: 0;">{group.member_count} cos.</span>
					</div>
					{#if group.latest_analysis_summary}
						<p
							style="font-family: var(--serif); font-size: 1.0625rem; line-height: 1.6; color: var(--ink-2); margin: 0 0 1.5rem; max-width: 60ch;"
						>
							{truncateSummary(group.latest_analysis_summary)}
						</p>
					{:else if group.description}
						<p
							style="font-family: var(--serif); font-size: 1.0625rem; line-height: 1.6; color: var(--ink-2); margin: 0 0 1.5rem; max-width: 60ch;"
						>
							{group.description}
						</p>
					{/if}
					<div
						class="flex-between"
						style="padding-top: 1.125rem; border-top: 1px solid var(--rule);"
					>
						{#if group.sic_codes && group.sic_codes.length > 0}
							<div style="display: flex; gap: 0.375rem; flex-wrap: wrap;">
								{#each group.sic_codes.slice(0, 3) as code (code)}
									<span class="tag" style="font-size: 10.5px;">SIC {code}</span>
								{/each}
								{#if group.sic_codes.length > 3}
									<span class="tag" style="font-size: 11px; background: transparent;"
										>+{group.sic_codes.length - 3}</span
									>
								{/if}
							</div>
						{:else}
							<div></div>
						{/if}
						<span style="font-size: 13px; color: var(--teal-2);">Open group &rarr;</span>
					</div>
				</a>
			{/each}
		</div>
	</section>
{:else}
	<section class="hairline-section" style="margin-top: 5rem;">
		<p class="body-text" style="color: var(--ink-3); padding: 3rem 0; text-align: center;">
			No groups found. Groups can be created via the CLI to organize companies for cross-company
			analysis.
		</p>
	</section>
{/if}

<style>
	.group-card {
		display: block;
		border: 1px solid var(--rule);
		border-radius: 8px;
		padding: 2rem;
		text-decoration: none;
		color: inherit;
		cursor: pointer;
		transition: border-color 0.15s;
	}
	.group-card:hover {
		border-color: var(--rule-2);
	}
</style>
