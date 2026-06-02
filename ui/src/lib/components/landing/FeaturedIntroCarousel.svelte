<script lang="ts">
	import type { FeaturedCompanyIntro } from '$lib/api-types';
	import { titleCase } from 'title-case';
	import { cleanContent } from '$lib/utils/filings';
	import { ArrowRight, ChevronLeft, ChevronRight } from '@lucide/svelte';

	let { companies }: { companies: FeaturedCompanyIntro[] } = $props();

	let current = $state(0);

	const count = $derived(companies.length);
	const active = $derived(companies[current]);

	function clamp(i: number): number {
		return Math.max(0, Math.min(i, count - 1));
	}
	function go(i: number) {
		current = clamp(i);
	}
	function prev() {
		go(current - 1);
	}
	function next() {
		go(current + 1);
	}

	function displayName(c: FeaturedCompanyIntro): string {
		return titleCase((c.display_name || c.name).toLowerCase());
	}

	/** First few sentences of the intro, cleaned of markdown/footnote noise. */
	function preview(text: string | null): string {
		const cleaned = cleanContent(text ?? '') ?? '';
		const sentences = cleaned.match(/[^.!?]+[.!?]+/g);
		if (!sentences) return cleaned.substring(0, 320);
		return sentences.slice(0, 3).join('').trim();
	}
</script>

{#if count > 0}
	<section class="hairline-section" style="margin-top: 5rem;">
		<div class="flex-between" style="align-items: flex-end; margin-bottom: 28px;">
			<div>
				<div class="eyebrow" style="margin-bottom: 10px;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;REAL EXAMPLES
				</div>
				<h2 class="section-heading">Company analyses, direct from the filings.</h2>
			</div>
			{#if active}
				<a
					href="/c/{active.ticker}"
					class="meta"
					style="color: var(--teal-2); text-decoration: none; white-space: nowrap;"
				>
					Open {active.ticker} &rarr;
				</a>
			{/if}
		</div>

		<div class="carousel">
			<div class="track" style="transform: translateX(-{current * 100}%);">
				{#each companies as c (c.ticker)}
					<div class="slide">
						<a href="/c/{c.ticker}" class="intro-card hover-card">
							<div
								class="flex-between"
								style="padding: 20px 28px; border-bottom: 1px solid var(--rule);"
							>
								<div style="display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;">
									<span class="tag" style="font-weight: 500; color: var(--ink);">{c.ticker}</span>
									<span style="font-family: var(--serif); font-size: 18px;">{displayName(c)}</span>
									{#if c.source_form_type}
										<span class="meta" style="color: var(--ink-4);">
											Sourced from Form {c.source_form_type}'s
										</span>
									{/if}
								</div>
								{#if c.source_filing_count > 0}
									<span class="meta" style="color: var(--ink-4); white-space: nowrap;">
										{c.source_filing_count} filings considered
									</span>
								{/if}
							</div>
							<div class="p-8">
								{#if c.intro}
									<p
										style="font-family: var(--serif); font-size: 17px; line-height: 1.65; color: var(--ink-2); margin: 0;"
										class="px-8"
									>
										{preview(c.intro)}
									</p>
								{:else if c.sic_description}
									<p
										style="font-family: var(--serif); font-size: 17px; line-height: 1.65; color: var(--ink-2); margin: 0;"
									>
										{c.sic_description}
									</p>
								{/if}
								<p class="flex justify-end pt-4 font-serif text-ink-3">
									Click to view the full filing timeline, change analysis, and AI-generated
									insights.
									<ArrowRight />
								</p>
							</div>
						</a>
					</div>
				{/each}
			</div>

			{#if count > 1}
				<button
					type="button"
					class="nav-btn nav-prev"
					onclick={prev}
					disabled={current === 0}
					aria-label="Previous company"
				>
					<ChevronLeft size={18} />
				</button>
				<button
					type="button"
					class="nav-btn nav-next"
					onclick={next}
					disabled={current === count - 1}
					aria-label="Next company"
				>
					<ChevronRight size={18} />
				</button>
			{/if}
		</div>

		{#if count > 1}
			<div class="dots">
				{#each companies as c, i (c.ticker)}
					<button
						type="button"
						class="dot"
						class:active={i === current}
						onclick={() => go(i)}
						aria-label="Show {c.ticker}"
						aria-current={i === current}
					></button>
				{/each}
			</div>
		{/if}
	</section>
{/if}

<style>
	.carousel {
		position: relative;
		overflow: hidden;
		border-radius: 8px;
	}
	.track {
		display: flex;
		transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
	}
	.slide {
		min-width: 100%;
		box-sizing: border-box;
	}
	.intro-card {
		display: block;
		border: 1px solid var(--rule);
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.15s;
	}
	.hover-card:hover {
		border-color: var(--rule-2) !important;
	}

	/* Prev / next controls */
	.nav-btn {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		border-radius: 999px;
		border: 1px solid var(--rule-2);
		background: var(--paper);
		color: var(--ink-2);
		cursor: pointer;
		transition:
			border-color 0.15s,
			color 0.15s,
			opacity 0.15s;
	}
	.nav-btn:hover:not(:disabled) {
		border-color: var(--ink-4);
		color: var(--ink);
	}
	.nav-btn:disabled {
		opacity: 0;
		pointer-events: none;
	}
	.nav-prev {
		left: 14px;
	}
	.nav-next {
		right: 14px;
	}

	/* Position indicators */
	.dots {
		display: flex;
		justify-content: center;
		gap: 8px;
		margin-top: 18px;
	}
	.dot {
		width: 7px;
		height: 7px;
		border-radius: 999px;
		border: 0;
		padding: 0;
		background: var(--rule-2);
		cursor: pointer;
		transition:
			background 0.15s,
			width 0.2s;
	}
	.dot:hover {
		background: var(--ink-4);
	}
	.dot.active {
		width: 22px;
		background: var(--teal-2);
	}
</style>
