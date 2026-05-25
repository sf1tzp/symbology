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
			In finance, a stock symbol represents a company's identity in the market. Symbology takes that
			idea further — turning raw SEC filings into clear, structured intelligence you can actually
			use.
		</p>

		<h2
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-top: 2.5rem; margin-bottom: 0.75rem; color: var(--ink);"
		>
			How does it work?
		</h2>
		<p>
			Symbology retrieves public filings directly from the SEC using the
			<a
				href="https://github.com/dgunning/edgartools"
				target="_blank"
				rel="noopener noreferrer"
				style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
				>edgartools</a
			>
			library. Each filing is broken into its component sections — often thousands of lines of dense,
			unstructured text.
		</p>
		<p>
			We then use large language models to distill each section into a consistent, readable format.
			By repeating this process across multiple reporting periods, Symbology can surface meaningful
			changes in a company's disclosures over time — automatically.
		</p>

		<h2
			style="font-family: var(--serif); font-size: 1.5rem; font-weight: 400; margin-top: 2.5rem; margin-bottom: 0.75rem; color: var(--ink);"
		>
			Why build this?
		</h2>
		<p>
			SEC filings are one of the most valuable sources of information about public companies, and
			one of the least accessible. They're long, inconsistent, and difficult to compare across years
			without significant manual effort.
		</p>
		<p>
			Symbology automates that work. No third-party data providers, no editorial interpretation —
			just structured analysis derived directly from primary sources.
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
	<div class="flex meta text-ink-3 my-4 justify-end ">
		<p>Have a question? Start a
		<a
			href="https://github.com/sf1tzp/symbology/discussions"
			target="_blank"
			rel="noopener noreferrer"
			style="color: var(--teal-2); text-decoration: none;">discussion on GitHub</a
		>.</p>
	</div>
</article>

