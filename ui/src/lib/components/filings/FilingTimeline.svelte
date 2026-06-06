<script lang="ts">
	import type { FilingTimelineResponse, CompanyResponse } from '$lib/api-types';
	import { formatFilingPeriod } from '$lib/utils/filings';

	interface Props {
		filings: FilingTimelineResponse[];
		company: CompanyResponse | null;
		selectedId?: string;
		/** Base path for each filing node link, e.g. "/f". */
		linkPrefix?: string;
		onselect?: (filing: FilingTimelineResponse) => void;
	}

	let { filings, company, selectedId = '', linkPrefix = '/f', onselect }: Props = $props();

	type Kind = 'annual' | 'quarterly' | 'other';
	type Filter = 'all' | 'annual' | 'quarterly' | 'other';

	const _FILTERS: { id: Filter; label: string }[] = [
		{ id: 'all', label: 'All filings' },
		{ id: 'annual', label: 'Annual' },
		// { id: 'quarterly', label: 'Quarterly' },
		{ id: 'other', label: 'Other' }
	];

	let filter = $state<Filter>('all');

	function kindOf(form: string): Kind {
		if (form.includes('10-K')) return 'annual';
		if (form.includes('10-Q')) return 'quarterly';
		return 'other';
	}

	function timeOf(f: FilingTimelineResponse): number {
		const d = new Date(f.period_of_report ?? f.filing_date);
		return isNaN(d.getTime()) ? 0 : d.getTime();
	}

	// Reuse the canonical fiscal-period logic (handles fiscal_year_end) and pull
	// the fiscal year out of its "FY 2024" / "FY 2024 Q1" label.
	function fiscalYearOf(f: FilingTimelineResponse): number {
		const m = formatFilingPeriod(f, company).match(/FY\s*(\d{4})/);
		if (m) return parseInt(m[1], 10);
		const d = new Date(f.period_of_report ?? f.filing_date);
		return isNaN(d.getTime()) ? 0 : d.getFullYear();
	}

	function shortForm(form: string): string {
		const k = kindOf(form);
		return k === 'annual' ? '10-K' : k === 'quarterly' ? '10-Q' : form;
	}

	// The newest annual filing carries the "Latest filing" callout; falls back to
	// the newest filing of any type when there's no 10-K.
	const latestAnnualId = $derived.by(() => {
		const annuals = filings.filter((f) => kindOf(f.form) === 'annual');
		const pool = annuals.length ? annuals : filings;
		let best: FilingTimelineResponse | null = null;
		for (const f of pool) if (!best || timeOf(f) >= timeOf(best)) best = f;
		return best?.id ?? '';
	});

	const activeSelectedId = $derived(selectedId || latestAnnualId);

	interface YearGroup {
		year: number;
		filings: FilingTimelineResponse[];
		quarters: number;
		hasAnnual: boolean;
		selected: boolean;
		/** Where a mobile year-chip tap leads: the year's 10-K, else its latest filing. */
		href: string;
		target: FilingTimelineResponse;
	}

	const years = $derived.by<YearGroup[]>(() => {
		const shown = filings.filter((f) => filter === 'all' || kindOf(f.form) === filter);
		const groups: Record<number, FilingTimelineResponse[]> = {};
		for (const f of shown) (groups[fiscalYearOf(f)] ??= []).push(f);
		return Object.keys(groups)
			.map(Number)
			.sort((a, b) => a - b)
			.map((year) => {
				const fs = groups[year].sort((a, b) => timeOf(a) - timeOf(b));
				const annual = fs.find((f) => kindOf(f.form) === 'annual');
				const target = annual ?? fs[fs.length - 1];
				return {
					year,
					filings: fs,
					quarters: fs.filter((f) => kindOf(f.form) === 'quarterly').length,
					hasAnnual: !!annual,
					selected: fs.some((f) => f.id === activeSelectedId),
					href: `${linkPrefix}/${target.accession_number}`,
					target
				};
			});
	});

	// Scroll both viewports to the newest year on mount.
	let desktopScroll = $state<HTMLDivElement | null>(null);
	let mobileScroll = $state<HTMLDivElement | null>(null);
	$effect(() => {
		void years;
		for (const el of [desktopScroll, mobileScroll]) {
			if (el) requestAnimationFrame(() => (el.scrollLeft = el.scrollWidth));
		}
	});
</script>

<!-- Filter pills (desktop only — mobile shows a compact year-chip scroller). -->
<!-- <div class="tl-filters">
	<div class="pillnav">
		{#each FILTERS as f (f.id)}
			<button class:active={filter === f.id} onclick={() => (filter = f.id)}>{f.label}</button>
		{/each}
	</div>
</div> -->

{#if years.length === 0}
	<p class="tl-empty">No filings match this filter.</p>
{:else}
	<!-- ── Desktop: year-axis with K/Q dots ── -->
	<div class="tl-scroll" bind:this={desktopScroll}>
		<div class="tl-track">
			<div class="tl-axis"></div>
			{#each years as y (y.year)}
				<div class="tl-col flex flex-col">
					<div class="tl-yr">FY{y.year}</div>
					<div class="tl-filings">
						{#each y.filings as f (f.id)}
							{@const kind = kindOf(f.form)}
							{@const isSel = f.id === activeSelectedId}
							{@const _isLatest = f.id === latestAnnualId}
							<a
								href="{linkPrefix}/{f.accession_number}"
								class="tl-dot {kind}"
								class:selected={isSel}
								aria-label="{f.form} · {formatFilingPeriod(f, company)}"
								onclick={() => onselect?.(f)}
							>
								<!-- {#if isLatest}<span class="tl-callout">Latest filing</span>{/if} -->
								{#if kind === 'annual'}<span class="tl-label">{shortForm(f.form)}</span>{/if}
							</a>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<!-- ── Mobile: horizontal year-chip scroller ── -->
	<div class="m-tl-scroll" bind:this={mobileScroll}>
		{#each years as y (y.year)}
			<a href={y.href} class="m-year" class:sel={y.selected} onclick={() => onselect?.(y.target)}>
				<div class="m-year-yr">FY{y.year}</div>
				<div class="m-year-dots">
					{#each y.filings as f (f.id)}
						<span class="m-year-dot {kindOf(f.form)}"></span>
					{/each}
				</div>
				<div class="m-year-note" class:sel={y.selected}>
					{y.selected ? 'Latest' : `${y.hasAnnual ? '10-K' : ''}`}
				</div>
			</a>
		{/each}
	</div>
{/if}

<!-- Legend -->
<!-- <div class="tl-legend">
	<span class="lg"><span class="lg-dot annual"></span> Annual report</span>
	<span class="lg"><span class="lg-dot quarterly"></span> Quarterly</span>
	<span class="lg"><span class="lg-dot selected"></span> Latest</span>
</div> -->

<style>
	.tl-filters {
		display: flex;
		justify-content: flex-end;
		margin-bottom: 1.25rem;
	}

	/* Pill filter */
	.pillnav {
		display: flex;
		gap: 4px;
		padding: 4px;
		background: var(--paper-2);
		border-radius: 10px;
		border: 1px solid var(--rule);
	}
	.pillnav button {
		appearance: none;
		border: 0;
		background: transparent;
		padding: 6px 14px;
		border-radius: 7px;
		font-family: var(--sans);
		font-size: 12.5px;
		font-weight: 500;
		color: var(--ink-3);
		cursor: pointer;
		transition: all 0.12s;
		white-space: nowrap;
	}
	.pillnav button.active {
		background: var(--paper);
		color: var(--ink);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.tl-empty {
		font-family: var(--mono);
		font-size: 12px;
		color: var(--ink-4);
		padding: 1.5rem 0;
	}

	/* ── Desktop axis ── */
	.tl-scroll {
		overflow-x: auto;
		scrollbar-width: thin;
	}
	.tl-track {
		position: relative;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(110px, 1fr);
		min-width: 100%;
		padding: 8px 0 28px;
	}
	.tl-axis {
		position: absolute;
		left: 0;
		right: 0;
		top: 47px;
		height: 1px;
		background: var(--rule);
	}
	.tl-col {
		margin-left: 16px;
		position: relative;
	}
	.tl-yr {
		font-family: var(--mono);
		font-size: 11px;
		letter-spacing: 0.08em;
		color: var(--ink-3);
		height: 14px;
		margin-bottom: 18px;
		top: 20px;
	}
	.tl-filings {
		display: flex;
		gap: 18px;
		align-items: center;
		height: 30px;
		position: relative;
		z-index: 1;
	}
	.tl-dot {
		--sz: 10px;
		top: -8px;
		width: var(--sz);
		height: var(--sz);
		border-radius: 50%;
		background: var(--paper);
		border: 1.5px solid var(--ink-4);
		position: relative;
		cursor: pointer;
		transition: transform 0.15s;
		text-decoration: none;
	}
	.tl-dot.annual {
		--sz: 24px;
		background: var(--ink-4);
		border-color: var(--ink);
	}
	/* Quarterly (10-Q) filings read in plum to set them apart from annual data. */
	.tl-dot.quarterly {
		background: var(--plum);
		border-color: var(--plum);
	}
	.tl-dot.other {
		border-style: dashed;
	}
	.tl-dot.selected {
		background: var(--teal-2);
		border-color: var(--teal-2);
		box-shadow: 0 0 0 4px var(--sage-2);
	}
	.tl-dot:hover {
		transform: scale(1.15);
	}
	.tl-label {
		position: absolute;
		top: calc(100% + 12px);
		left: 50%;
		transform: translateX(-50%);
		font-family: var(--mono);
		font-size: 10px;
		color: var(--ink-2);
		white-space: nowrap;
	}
	.tl-callout {
		position: absolute;
		bottom: -34px;
		left: 50%;
		transform: translateX(-50%);
		font-family: var(--mono);
		font-size: 10.5px;
		color: var(--teal-2);
		background: var(--sage-2);
		padding: 4px 8px;
		border-radius: 4px;
		white-space: nowrap;
	}
	/* .tl-callout::after {
		content: '';
		position: absolute;
		top: -10px;
		left: 50%;
		transform: translateX(-50%);
		width: 1px;
		height: 10px;
		background: var(--teal-2);
	} */

	/* ── Mobile year chips ── */
	.m-tl-scroll {
		display: none;
		gap: 12px;
		overflow-x: auto;
		padding: 2px 0 8px;
		scroll-snap-type: x proximity;
		scrollbar-width: none;
	}
	.m-tl-scroll::-webkit-scrollbar {
		display: none;
	}
	.m-year {
		flex: 0 0 auto;
		width: 96px;
		padding: 14px;
		border-radius: 12px;
		border: 1px solid var(--rule);
		background: var(--paper);
		display: flex;
		flex-direction: column;
		gap: 10px;
		scroll-snap-align: start;
		text-decoration: none;
		color: inherit;
	}
	.m-year.sel {
		border-color: var(--teal-2);
		background: var(--sage-2);
	}
	.m-year-yr {
		font-family: var(--mono);
		font-size: 11px;
		color: var(--ink-3);
		letter-spacing: 0.06em;
	}
	.m-year-dots {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.m-year-dot {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--paper);
		border: 1.5px solid var(--ink-4);
	}
	.m-year-dot.annual {
		background: var(--ink);
		border-color: var(--ink);
	}
	.m-year-dot.quarterly {
		background: var(--plum);
		border-color: var(--plum);
	}
	.m-year-dot.other {
		border-style: dashed;
	}
	.m-year.sel .m-year-dot.annual {
		background: var(--teal-2);
		border-color: var(--teal-2);
	}
	.m-year-note {
		font-family: var(--mono);
		font-size: 10px;
		color: var(--ink-4);
	}
	.m-year-note.sel {
		color: var(--teal-2);
	}

	/* ── Legend ── */
	.tl-legend {
		display: flex;
		gap: 1.25rem;
		margin-top: 1rem;
		flex-wrap: wrap;
	}
	.lg {
		display: flex;
		align-items: center;
		gap: 8px;
		font-family: var(--mono);
		font-size: 12px;
		color: var(--ink-3);
	}
	.lg-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex: 0 0 auto;
	}
	.lg-dot.annual {
		width: 12px;
		height: 12px;
		background: var(--ink);
	}
	.lg-dot.quarterly {
		background: var(--paper);
		border: 1.5px solid var(--ink-4);
	}
	.lg-dot.selected {
		background: var(--teal-2);
		box-shadow: 0 0 0 3px var(--sage-2);
	}

	/* Swap axis ↔ chips at the md breakpoint. */
	@media (max-width: 767.98px) {
		.tl-filters,
		.tl-scroll {
			display: none;
		}
		.m-tl-scroll {
			display: flex;
		}
	}
</style>
