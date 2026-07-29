<script lang="ts">
	import type { CompanyResponse, ShowcaseCompany, ShowcaseSourceFiling } from '$lib/api-types';
	import DiffView from '$lib/components/DiffView.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { getAnalysisTypeDisplay } from '$lib/utils/filings';
	import { docColor } from '$lib/utils/changes';
	import { titleCase } from 'title-case';
	import { ChevronLeft, ChevronRight } from '@lucide/svelte';

	let { companies }: { companies: ShowcaseCompany[] } = $props();

	let current = $state(0);

	// The scroll-snap viewport (mobile) — also drives `current` from scroll position.
	let viewport = $state<HTMLDivElement | null>(null);
	// Below md we navigate via native scroll-snap; at md+ we use the JS translateX track.
	let snapMode = $state(false);

	const count = $derived(companies.length);

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

	function displayName(c: ShowcaseCompany): string {
		return titleCase((c.display_name || c.name).toLowerCase());
	}

	// Fiscal-year chip label for a source-filing citation, e.g. "’24".
	function fyShort(f: ShowcaseSourceFiling): string {
		const iso = f.periodOfReport ?? f.filingDate;
		return iso ? `’${iso.slice(2, 4)}` : f.form;
	}

	// DiffView only reads fiscal_year_end off the company (for fiscal-period labels).
	function companyForPeriods(c: ShowcaseCompany): CompanyResponse {
		return { fiscal_year_end: c.fiscal_year_end } as CompanyResponse;
	}

	function changesHref(c: ShowcaseCompany): string {
		return c.diff
			? `/c/${c.ticker}/changes/${c.diff.documentType}#diff-${c.diff.sectionDiffId}`
			: '';
	}

	const MAX_CITATIONS = 4;
</script>

{#if count > 0}
	<section class="hairline-section">
		<div class="mb-10 grid grid-cols-1 gap-6 md:grid-cols-[1.4fr_1fr] md:items-end">
			<div>
				<div class="eyebrow mb-2.5">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;REAL EXAMPLES &middot; DRAWN AT RANDOM
				</div>
				<h2 class="section-heading">
					Read the brief. <em class="font-light text-ink-3">See what changed.</em>
				</h2>
			</div>
			<p
				class="body-text m-0 max-w-[46ch] text-[15px] leading-[1.6] text-ink-2 md:justify-self-end"
			>
				Every company page pairs a readable brief — synthesized from years of filings — with
				word-by-word diffs of the disclosures behind it, each one a click from its source document.
			</p>
		</div>

		<!--
			Mobile: a horizontal scroll-snap viewport (swipe to page). md+: overflow is
			clipped and the track is positioned with translateX instead (arrows + tabs).
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
						<article class="flex h-full flex-col overflow-hidden rounded-lg border border-rule">
							<!-- Masthead: identity left, provenance right -->
							<header
								class="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b border-rule px-5 py-4 md:px-7 md:py-5"
							>
								<div class="min-w-0">
									<div class="flex flex-wrap items-baseline gap-3">
										<a
											href="/c/{c.ticker}"
											class="font-serif text-[22px] leading-tight text-ink no-underline transition-colors duration-150 hover:text-teal-2"
										>
											{displayName(c)}
										</a>
										<span class="tag font-medium text-ink">{c.ticker}</span>
									</div>
									{#if c.sic_description}
										<div class="mt-1 font-serif text-xs text-ink-4 italic">
											{c.sic_description}
										</div>
									{/if}
								</div>
								{#if c.sourceFilings.length > 0}
									<div class="flex flex-col gap-1.5 md:items-end">
										<span class="eyebrow text-[10.5px]">
											Synthesized from {c.source_filing_count} Form
											{c.source_form_type ?? 'filing'}{c.source_filing_count === 1 ? '' : 's'}
										</span>
										<div class="flex flex-wrap items-baseline gap-1.5">
											{#each c.sourceFilings.slice(0, MAX_CITATIONS) as f (f.accessionNumber)}
												<a
													href="/f/{f.accessionNumber}"
													class="rounded border border-rule px-1.5 py-0.5 font-mono text-[11px] text-ink-3 no-underline transition-colors duration-150 hover:border-teal-2 hover:text-teal-2"
													title="{f.form} filing"
												>
													{f.form}&nbsp;{fyShort(f)}
												</a>
											{/each}
											{#if c.sourceFilings.length > MAX_CITATIONS}
												<span class="font-mono text-[11px] text-ink-4">
													+{c.sourceFilings.length - MAX_CITATIONS}
												</span>
											{/if}
										</div>
									</div>
								{/if}
							</header>

							<!-- Body: the brief (reading column) | the latest change (annotation rail) -->
							<div class="grid flex-1 grid-cols-1 {c.diff ? 'lg:grid-cols-[1.15fr_1fr]' : ''}">
								<div class="flex flex-col p-5 md:p-7 lg:p-8">
									<div class="eyebrow mb-5">
										<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;THE BRIEF
									</div>
									<div class="relative max-h-[19rem] overflow-hidden md:max-h-[21rem]">
										<div class="analysis-body {c.diff ? '' : 'max-w-[68ch]'}">
											<MarkdownContent content={c.briefParagraphs.join('\n\n')} />
										</div>
										<!-- Fade the teaser out into the page instead of cutting it off. -->
										<div
											class="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-linear-to-b from-transparent to-paper"
										></div>
									</div>
									<div class="relative z-10 -mt-4 pt-0">
										<a
											href="/c/{c.ticker}"
											class="inline-flex cursor-pointer items-center justify-center rounded-lg border border-rule-2 bg-paper px-[18px] py-2.5 font-sans text-[13px] font-medium text-ink no-underline transition-colors duration-150 hover:border-ink-4"
										>
											Continue reading &rarr;
										</a>
									</div>
								</div>

								{#if c.diff}
									<div
										class="flex flex-col border-t border-rule bg-paper-2/60 p-5 md:p-7 lg:border-t-0 lg:border-l lg:p-8"
									>
										<div class="mb-4 flex flex-wrap items-center justify-between gap-2">
											<div class="eyebrow">
												<span style="color: {docColor(c.diff.documentType)};">&#9679;</span
												>&nbsp;&nbsp;LATEST CHANGE &middot; {getAnalysisTypeDisplay(
													c.diff.documentType
												)}
											</div>
											<ChangeKindTag changeKind={c.diff.changeKind} />
										</div>
										{#if c.diff.heading}
											<h3
												class="mt-0 mb-1 font-serif text-[19px] leading-[1.3] tracking-[-0.01em] text-ink"
											>
												{c.diff.heading}
											</h3>
										{/if}
										{#if c.diff.sectionPath}
											<div class="meta mb-4 text-xs text-ink-4">{c.diff.sectionPath}</div>
										{/if}
										{#if c.diff.summary}
											<p
												class="mt-0 mb-6 border-l-2 border-teal-2 pl-3.5 font-serif text-[15px] leading-[1.55] text-ink-2"
											>
												{c.diff.summary}
											</p>
										{/if}
										<!-- Stack the compare columns: the rail is too narrow for side-by-side. -->
										<div class="[&_.compare]:grid-cols-1 [&_.compare]:gap-5 [&_.diff-block]:mb-0">
											<DiffView
												topic={{
													sectionPath: c.diff.sectionPath,
													heading: c.diff.heading,
													changeKind: c.diff.changeKind,
													ops: c.diff.ops,
													truncated: c.diff.truncated
												}}
												leftFiling={c.diff.leftFiling}
												rightFiling={c.diff.rightFiling}
												company={companyForPeriods(c)}
											/>
										</div>
										<div class="mt-auto flex justify-end pt-5">
											<a
												href={changesHref(c)}
												class="meta text-sm whitespace-nowrap text-teal-2 no-underline"
											>
												See more {c.ticker} changes &rarr;
											</a>
										</div>
									</div>
								{/if}
							</div>
						</article>
					</div>
				{/each}
			</div>

			{#if count > 1}
				<button
					type="button"
					class="absolute top-1/2 left-4 hidden size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full border border-rule-2 bg-paper text-ink-2 transition duration-150 enabled:hover:border-ink-4 enabled:hover:text-ink disabled:pointer-events-none disabled:opacity-0 md:flex"
					onclick={() => go(current - 1)}
					disabled={current === 0}
					aria-label="Previous company"
				>
					<ChevronLeft size={18} />
				</button>
				<button
					type="button"
					class="absolute top-1/2 right-4 hidden size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full border border-rule-2 bg-paper text-ink-2 transition duration-150 enabled:hover:border-ink-4 enabled:hover:text-ink disabled:pointer-events-none disabled:opacity-0 md:flex"
					onclick={() => go(current + 1)}
					disabled={current === count - 1}
					aria-label="Next company"
				>
					<ChevronRight size={18} />
				</button>
			{/if}
		</div>

		{#if count > 1}
			<!-- Specimen index: ticker tabs instead of anonymous dots. -->
			<div class="mt-7 flex flex-wrap items-center justify-center gap-2">
				{#each companies as c, i (c.ticker)}
					<button
						type="button"
						class="cursor-pointer rounded-full border px-3 py-1.5 font-mono text-[11.5px] tracking-[0.04em] uppercase transition-all duration-200 {i ===
						current
							? 'border-ink bg-ink text-paper'
							: 'border-rule bg-transparent text-ink-3 hover:border-rule-2 hover:text-ink'}"
						onclick={() => go(i)}
						aria-label="Show {c.ticker}"
						aria-current={i === current}
					>
						{c.ticker}
					</button>
				{/each}
			</div>
			<p class="meta mt-4 text-center text-xs text-ink-4">
				A new selection every visit &middot; drawn from hundreds of synthesized companies
			</p>
		{/if}
	</section>
{/if}
