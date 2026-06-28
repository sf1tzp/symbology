<script lang="ts">
	import { ChevronRight } from '@lucide/svelte';
	import type { Snippet } from 'svelte';

	// A coloured change card with a left accent bar. Callers pick the accent (per
	// document type or per change kind) and supply the header content. The main line
	// prefers `summary` (the generated "what changed" prose) and falls back to
	// `heading` (the raw topic text) when there's no summary; a footer-left snippet
	// (e.g. a section path) fills out the foot. `dot` shows a small accent dot before the
	// header — off where the header already carries a coloured tag. The "Open →"
	// affordance is always present.
	let {
		href,
		accent = 'var(--ink-3)',
		dot = true,
		heading = null,
		summary = null,
		onclick,
		header,
		footerLeft
	}: {
		href: string;
		accent?: string;
		dot?: boolean;
		heading?: string | null;
		summary?: string | null;
		onclick?: (e: MouseEvent) => void;
		header: Snippet;
		footerLeft?: Snippet;
	} = $props();
</script>

<a {href} {onclick} class="change-card" style="--card-accent: {accent};">
	<div class="hd">
		{#if dot}
			<span class="hd-dot" style="background: {accent};"></span>
		{/if}
		{@render header()}
	</div>
	<!-- Prefer the generated summary as the card's main line; fall back to the raw
	     topic heading (often just a table fragment) only when there's no summary. -->
	{#if summary}
		<div class="ti">{summary}</div>
	{:else if heading}
		<div class="ti">{heading}</div>
	{/if}
	<div class="ft">
		<span class="ft-left"
			>{#if footerLeft}{@render footerLeft()}{/if}</span
		>
		<span>Open <ChevronRight class="inline h-3 w-3" /></span>
	</div>
</a>

<style>
	.change-card {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		/* Let the card shrink inside grid/flex parents, and break long unbroken
		   tokens, so a wide summary never forces horizontal page overflow. */
		min-width: 0;
		overflow-wrap: break-word;
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--rule);
		border-left: 3px solid var(--card-accent, var(--teal-2));
		border-radius: 0 8px 8px 0;
		text-decoration: none;
		color: inherit;
		transition:
			border-color 0.15s,
			background 0.1s;
	}
	/* .change-card:hover {
		border-color: var(--rule-2);
		background: var(--paper-2);
	} */
	.change-card .hd {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 15px;
		font-weight: 600;
		color: var(--ink);
	}
	.change-card .hd-dot {
		width: 8px;
		height: 8px;
		border-radius: 9999px;
		flex-shrink: 0;
	}
	.change-card .ti {
		font-family: var(--serif);
		font-size: 16px;
		line-height: 1.4;
		color: var(--ink);
	}
	.change-card .ft {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: auto;
		padding-top: 0.5rem;
		font-size: 12px;
		color: var(--ink-4);
	}
</style>
