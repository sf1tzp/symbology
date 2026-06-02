<script lang="ts">
	import { ChevronLeft } from '@lucide/svelte';
	import { onMount } from 'svelte';

	interface PlatformStats {
		companies: number;
		filings: number;
		documents: number;
		earliest_year: number | null;
	}

	let stats = $state<PlatformStats | null>(null);

	function formatStatValue(n: number): string {
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
		if (n >= 1_000) return n.toLocaleString();
		return String(n);
	}

	onMount(async () => {
		const res = await fetch('/api/stats');
		if (res.ok) {
			stats = await res.json();
		}
	});
</script>

<svelte:head>
	<title>How it works - Symbology</title>
	<meta
		name="description"
		content="How Symbology turns raw SEC filings into structured financial intelligence"
	/>
</svelte:head>

<!-- Back link -->
<div style="margin-bottom: 3rem;">
	<a
		href="/"
		class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3 w-3" />
		Home
	</a>
</div>

<!-- Masthead -->
<header style="max-width: 720px;">
	<div class="eyebrow" style="margin-bottom: 1rem;">
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;HOW IT WORKS
	</div>
	<h1 class="display" style="margin-bottom: 1rem;">
		From filings<br />
		<em>to insight.</em>
	</h1>
	<p class="lede" style="color: var(--ink-2); max-width: 52ch;">
		Symbology turns raw SEC filings into structured, comparable intelligence — automatically, from
		primary sources.
	</p>
</header>

<!-- Content -->
<article style="margin-top: 5rem;">
	<div class="analysis-body">
		<h2
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-bottom: 0.75rem; color: var(--ink);"
		>
			What is Symbology?
		</h2>
		<p>
			A stock symbol is a company's shorthand identity in the market. Symbology extends that idea to
			the company's own words — turning the raw SEC filings behind a ticker into clear, structured,
			comparable intelligence.
		</p>

		<h2
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-top: 2.5rem; margin-bottom: 0.75rem; color: var(--ink);"
		>
			How does it work?
		</h2>
		<p>
			Symbology pulls public filings straight from the SEC with the
			<a
				href="https://github.com/dgunning/edgartools"
				target="_blank"
				rel="noopener noreferrer"
				style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
				>edgartools</a
			>
			library and splits each one into its component sections — risk factors, management's discussion,
			business description, and the rest — often thousands of lines of dense, unstructured text.
		</p>
		<p>
			From there, large language models distill those sections and compare them across reporting
			periods to surface what actually changed. That synthesis happens in deliberate stages,
			described below.
		</p>

		<h2
			id="synthesis-levels"
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-top: 2.5rem; margin-bottom: 0.75rem; color: var(--ink); scroll-margin-top: 5rem;"
		>
			What are synthesis levels?
		</h2>
		<p>
			Every piece of generated analysis carries a <strong>synthesis level</strong> — labelled L1 through
			L4 — that records how many steps of generation separate it from the original filing text. Each level
			is built only from the level beneath it, so the analysis forms a traceable chain rooted in primary
			source material.
		</p>
		<div style="margin: 1.5rem 0; display: flex; flex-direction: column; gap: 1rem;">
			<div
				style="display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: baseline;"
			>
				<span
					style="font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: var(--teal-2);"
					>L1</span
				>
				<div>
					<strong style="color: var(--ink);">Section summary</strong> — generated directly from a single
					filing section. The source material is the document itself.
				</div>
			</div>
			<div
				style="display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: baseline;"
			>
				<span
					style="font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: var(--teal-2);"
					>L2</span
				>
				<div>
					<strong style="color: var(--ink);">Change report</strong> — generated from a collection of L1
					summaries of the same section across reporting periods.
				</div>
			</div>
			<div
				style="display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: baseline;"
			>
				<span
					style="font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: var(--teal-2);"
					>L3</span
				>
				<div>
					<strong style="color: var(--ink);">Page content</strong> — generated from an L2 report — the
					editorial narrative you read on a company or filing page.
				</div>
			</div>
			<div
				style="display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: baseline;"
			>
				<span
					style="font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: var(--teal-2);"
					>L4</span
				>
				<div>
					<strong style="color: var(--ink);">Lead</strong> — generated from L3. Brief introductions, used
					sparingly.
				</div>
			</div>
		</div>
		<p>
			Our prompting strategy shifts deliberately as the level rises. <strong>L1</strong> is direct
			and fact-oriented — a faithful distillation of a single section. <strong>L2</strong>
			gathers those summaries across years and surfaces what changed and what recurred over time.
			<strong>L3</strong>
			is editorial, weaving those trends into a readable narrative.
			<strong>L4</strong> is reserved for the short leads that orient a reader before they dive in.
		</p>
		<p>
			We are deliberately cautious about extending this chain too far. Each additional level moves
			further from the source text and compounds the risk of hallucination, so we stop well before
			the analysis becomes untethered from what the filings actually say. To keep every statement
			verifiable, the full chain of generation — and the source documents at its root — stays
			visible, so a higher-level claim can always be traced back through the levels that produced
			it.
		</p>

		<h2
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-top: 2.5rem; margin-bottom: 0.75rem; color: var(--ink);"
		>
			Why build this?
		</h2>
		<p>
			SEC filings are among the most valuable sources of information about public companies, and
			among the least accessible — long, inconsistent, and hard to compare across years without
			significant manual effort.
		</p>
		<p>
			Symbology automates that work end to end, from primary sources. No third-party data feeds and
			no opinions layered on top: the analysis turns editorial only where it helps a reader, and
			every statement traces back through its synthesis levels to the filing it came from.
		</p>
	</div>

	<!-- Stats -->
	{#if stats}
		<div
			class="grid-4"
			style="margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);"
		>
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.companies)}</span>
				<span class="stat-label">Public Companies Indexed</span>
			</div>
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.filings)}</span>
				<span class="stat-label">Filings Parsed</span>
			</div>
			<div class="stat">
				<span class="stat-value">{formatStatValue(stats.documents)}</span>
				<span class="stat-label">Sections Analysed</span>
			</div>
			{#if stats.earliest_year}
				<div class="stat">
					<span class="stat-value">FY{stats.earliest_year}</span>
					<span class="stat-label">Earliest Filing</span>
				</div>
			{/if}
		</div>
	{/if}
	<div class="meta my-4 flex justify-end text-ink-3">
		<p>
			Have a question? Start a
			<a
				href="https://github.com/sf1tzp/symbology/discussions"
				target="_blank"
				rel="noopener noreferrer"
				style="color: var(--teal-2); text-decoration: none;">discussion on GitHub</a
			>.
		</p>
	</div>
</article>
