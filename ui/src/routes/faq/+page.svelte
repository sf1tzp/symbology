<script lang="ts">
	import SectionHead from '$lib/components/SectionHead.svelte';
	import { ChevronLeft } from '@lucide/svelte';
</script>

<svelte:head>
	<title>How it works - Symbology</title>
	<meta
		name="description"
		content="How Symbology turns raw SEC filings into structured financial intelligence"
	/>
</svelte:head>

<!-- Back link -->
<div class="hidden md:block" style="margin-bottom: 3rem;">
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
		<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;FREQUENTLY ASKED QUESTIONS
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
		<section>
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Frequently asked questions"
				heading="What is Symbology?"
			/>
			<p>
				A stock symbol is a company's shorthand identity in the market. Symbology extends that idea
				to the company's own words — turning the raw SEC filings behind a ticker into clear,
				structured, comparable intelligence.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Frequently asked questions"
				heading="How does it work?"
			/>
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
		</section>

		<section id="synthesis-vs-analysis" style="margin-top: 3rem; scroll-margin-top: 5rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Frequently asked questions"
				heading="Synthesis is NOT Analysis"
			/>
			<p>
				Symbology surfaces <strong style="color: var(--ink);">what changed</strong> — what a company
				added, dropped, or reworded from one filing to the next. It does not weigh those changes,
				judge them, or tell you what to do about them. You will not find ratings, price targets, or
				recommendations anywhere on the site, and nothing here is investment advice. Our
				<a
					href="/terms#not-investment-advice"
					style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
					>Terms of Service</a
				> set out the specific disclaimers in full.
			</p>
			<p>
				Because every summary is written by a language model, we make the work checkable rather than
				ask you to take it on faith. Each piece of synthesis has a source view — its
				<span style="font-family: var(--mono);">/s/</span> route — that shows exactly how it was produced:
				the system prompt, the model configuration, and the source filing text passed in as the user prompt.
				Any claim can be traced back to the words it came from.
			</p>
			<p>
				See something off? If a passage looks wrong or misleading, tell us at
				<a
					href="mailto:support@streetfortress.com"
					style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
					>support@streetfortress.com</a
				>.
			</p>
		</section>

		<section id="synthesis-levels" style="margin-top: 3rem; scroll-margin-top: 5rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Frequently asked questions"
				heading="What are synthesis levels?"
			/>
			<p>
				Every piece of generated synthesis carries a <strong>synthesis level</strong> — labelled L1 through
				L4 — that records how many steps of generation separate it from the original filing text. Each
				level is built only from the level beneath it, so the synthesis forms a traceable chain rooted
				in primary source material.
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
						<strong style="color: var(--ink);">Change report</strong> — generated from a collection of
						L1 summaries of the same section across reporting periods.
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
						<strong style="color: var(--ink);">Lead</strong> — generated from L3. Brief introductions,
						used sparingly.
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
				the synthesis becomes untethered from what the filings actually say. To keep every statement
				verifiable, the full chain of generation — and the source documents at its root — stays
				visible, so a higher-level claim can always be traced back through the levels that produced
				it.
			</p>
		</section>

		<section id="text-diffs" style="margin-top: 3rem; scroll-margin-top: 5rem;">
			<SectionHead
				sticky
				stickyHeading
				eyebrow="Frequently asked questions"
				heading="What are Text Diffs?"
			/>
			<p>
				A text diff is a visual aid for highlighting the changes between two documents. By
				convention, the left column is the <strong style="color: var(--ink);">old</strong> side of
				the diff and the right column is the <strong style="color: var(--ink);">new</strong> side.
				Content that was removed from the old document is
				<span class="del">highlighted in red</span>, and content that was added in the new document
				is <span class="ins">highlighted in green</span>.
			</p>

			<!-- Brief worked example of the left/right diff display. -->
			<div class="compare" style="margin: 1.75rem 0;">
				<div class="compare-col">
					<h4>
						<span>FY2023 10-K</span>
						<span class="del" style="padding: 2px 8px;">Removed</span>
					</h4>
					<div class="compare-text">
						<p>Competition in our industry is <span class="del">significant.</span></p>
					</div>
				</div>
				<div class="compare-col">
					<h4>
						<span>FY2024 10-K</span>
						<span class="ins" style="padding: 2px 8px;">Added</span>
					</h4>
					<div class="compare-text">
						<p>Competition in our industry is <span class="ins">intense and increasing.</span></p>
					</div>
				</div>
			</div>

			<p>
				On mobile devices we only show the side of the diff that best captures the change.
				Side-by-side diffs are best experienced on a computer or tablet.
			</p>
			<p>
				To pair up comparable passages between two filings, we use a technique called
				<a
					href="https://en.wikipedia.org/wiki/Word_embedding"
					target="_blank"
					rel="noopener noreferrer"
					style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
					>word embedding</a
				>
				to match sections that discuss similar topics. This isn't an exact science, and it sometimes produces
				lacklustre diffs — but many are genuinely informative, and the same embeddings help power our
				advanced search. We aim to improve the signal-to-noise ratio of this feature over time.
			</p>
		</section>

		<section style="margin-top: 3rem;">
			<SectionHead heading="Why build this?" />
			<p>
				SEC filings are among the most valuable sources of information about public companies, and
				among the least accessible — long, inconsistent, and hard to compare across years without
				significant manual effort.
			</p>
			<p>
				Symbology automates that work end to end, from primary sources. No third-party data feeds
				and no opinions layered on top: the synthesis turns editorial only where it helps a reader,
				and every statement traces back through its synthesis levels to the filing it came from.
			</p>
		</section>
	</div>

	<div class="meta mt-6 flex justify-start border-t pt-6 text-ink-3 md:justify-end">
		<p>
			Have a question? Contact us
			<a
				href="mailto:support@streetfortress.com"
				style="color: var(--teal-2); text-decoration: underline; text-underline-offset: 3px;"
				>support@streetfortress.com</a
			>.
		</p>
	</div>
</article>
