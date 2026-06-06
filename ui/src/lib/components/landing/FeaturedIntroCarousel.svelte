<script lang="ts">
	import type { FeaturedCompanyIntro } from '$lib/api-types';
	import { titleCase } from 'title-case';
	import { ArrowRight, ChevronLeft, ChevronRight } from '@lucide/svelte';
	import { previewContent } from '$lib/utils';

	let { companies }: { companies: FeaturedCompanyIntro[] } = $props();

	let current = $state(0);

	// The scroll-snap viewport (mobile) — also drives `current` from scroll position.
	let viewport = $state<HTMLDivElement | null>(null);
	// Below md we navigate via native scroll-snap; at md+ we use the JS translateX track.
	let snapMode = $state(false);

	const count = $derived(companies.length);
	const active = $derived(companies[current]);

	function clamp(i: number): number {
		return Math.max(0, Math.min(i, count - 1));
	}
	function go(i: number) {
		const target = clamp(i);
		if (snapMode && viewport) {
			// Let the scroll handler sync `current`; just move the viewport.
			viewport.scrollTo({ left: target * viewport.clientWidth, behavior: 'smooth' });
		} else {
			current = target;
		}
	}
	function prev() {
		go(current - 1);
	}
	function next() {
		go(current + 1);
	}

	/** Derive the active slide from the snap viewport's scroll offset (mobile). */
	function onScroll() {
		if (!snapMode || !viewport) return;
		current = clamp(Math.round(viewport.scrollLeft / viewport.clientWidth));
	}

	$effect(() => {
		const mq = window.matchMedia('(max-width: 767.98px)');
		const sync = () => (snapMode = mq.matches);
		sync();
		mq.addEventListener('change', sync);
		return () => mq.removeEventListener('change', sync);
	});

	function displayName(c: FeaturedCompanyIntro): string {
		return titleCase((c.display_name || c.name).toLowerCase());
	}
</script>

{#if count > 0}
	<section class="hairline-section mt-20 mb-4">
		<div class="flex-between mb-7 items-end">
			<div>
				<div class="eyebrow mb-2.5">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;REAL EXAMPLES
				</div>
				<!-- <h2 class="section-heading">Generated Analysis, direct from the filings.</h2> -->
			</div>
			{#if active}
				<a
					href="/c/{active.ticker}"
					class="meta hidden whitespace-nowrap text-teal-2 no-underline md:block"
				>
					Open {active.ticker} &rarr;
				</a>
			{/if}
		</div>

		<!--
			Mobile: a horizontal scroll-snap viewport (swipe to page). md+: overflow is
			clipped and the track is positioned with translateX instead (arrows + dots).
			Scrollbar is hidden; `current` syncs from scrollLeft via onScroll.
		-->
		<div
			bind:this={viewport}
			onscroll={onScroll}
			class="relative snap-x snap-mandatory [scrollbar-width:none] overflow-x-auto overflow-y-hidden rounded-lg [-ms-overflow-style:none] md:snap-none md:overflow-hidden [&::-webkit-scrollbar]:hidden"
		>
			<div
				class="flex transition-transform duration-[400ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
				style:transform={snapMode ? undefined : `translateX(-${current * 100}%)`}
			>
				{#each companies as c (c.ticker)}
					<div class="w-full shrink-0 snap-start">
						<a
							href="/c/{c.ticker}"
							class="flex h-full flex-col overflow-hidden rounded-lg border border-rule text-inherit no-underline transition-colors duration-150 hover:border-rule-2"
						>
							<div
								class="flex-between flex-wrap gap-x-3 gap-y-1 border-b border-rule px-5 py-4 md:px-7 md:py-5"
							>
								<div class="flex flex-wrap items-baseline gap-3.5">
									<div class="flex-between flex">
										<span class="font-serif text-xl">{displayName(c)}</span>
										<span class="tag ml-2 font-medium text-ink">{c.ticker}</span>
									</div>
								</div>
								{#if c.source_form_type}
									<span class="meta text-xs text-ink-4">
										Synthesized from Form {c.source_form_type}'s
									</span>
								{/if}
								{#if c.source_filing_count > 0}
									<span class="meta hidden text-xs whitespace-nowrap text-ink-4 md:block">
										{c.source_filing_count} filings considered
									</span>
								{/if}
							</div>
							<div class="flex flex-1 flex-col p-6 md:p-8">
								{#if c.intro}
									<p
										class="m-0 line-clamp-8 font-serif text-[17px] leading-[1.65] text-ink-2 md:px-8"
									>
										{previewContent(c.intro)}
									</p>
								{:else if c.sic_description}
									<p class="m-0 line-clamp-4 font-serif text-[17px] leading-[1.65] text-ink-2">
										{c.sic_description}
									</p>
								{/if}
								<p class="mt-auto flex justify-end pt-4 font-serif text-teal-2 md:hidden">
									Open {active.ticker} &rarr;
								</p>
								<p class="mt-auto hidden justify-end pt-4 font-serif text-ink-3 md:flex">
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
					class="absolute top-1/2 left-4 hidden size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full border border-rule-2 bg-paper text-ink-2 transition duration-150 enabled:hover:border-ink-4 enabled:hover:text-ink disabled:pointer-events-none disabled:opacity-0 md:flex"
					onclick={prev}
					disabled={current === 0}
					aria-label="Previous company"
				>
					<ChevronLeft size={18} />
				</button>
				<button
					type="button"
					class="absolute top-1/2 right-4 hidden size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full border border-rule-2 bg-paper text-ink-2 transition duration-150 enabled:hover:border-ink-4 enabled:hover:text-ink disabled:pointer-events-none disabled:opacity-0 md:flex"
					onclick={next}
					disabled={current === count - 1}
					aria-label="Next company"
				>
					<ChevronRight size={18} />
				</button>
			{/if}
		</div>

		{#if count > 1}
			<div class="mt-8 flex flex-wrap justify-center gap-2">
				{#each companies as c, i (c.ticker)}
					<button
						type="button"
						class="h-[7px] cursor-pointer rounded-full border-0 p-0 transition-all duration-200 {i ===
						current
							? 'w-[22px] bg-teal-2'
							: 'w-[7px] bg-rule-2 hover:bg-ink-4'}"
						onclick={() => go(i)}
						aria-label="Show {c.ticker}"
						aria-current={i === current}
					></button>
				{/each}
			</div>
		{/if}
	</section>
{/if}
