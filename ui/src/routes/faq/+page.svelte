<script lang="ts">
	import { Card, CardContent } from '$lib/components/ui/card';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let content = `
## What is Symbology?

In finance, a stock symbol represents a company's identity in the market. Symbology takes that idea further — turning raw SEC filings into clear, structured intelligence you can actually use.

## How does it work?

Symbology retrieves public filings directly from the SEC using the [edgartools](https://github.com/dgunning/edgartools) library. Each filing is broken into its component sections — often thousands of lines of dense, unstructured text.

We then use large language models to distill each section into a consistent, readable format. By repeating this process across multiple reporting periods, Symbology can surface meaningful changes in a company's disclosures over time — automatically.

## Why build this?

SEC filings are one of the most valuable sources of information about public companies, and one of the least accessible. They're long, inconsistent, and difficult to compare across years without significant manual effort.

Symbology automates that work. No third-party data providers, no editorial interpretation — just structured analysis derived directly from primary sources.

- Thousands of participating companies
- New filings published on a regular cadence
- Standardized reporting that enables meaningful comparison over time

---

Have a question? Start a [discussion on GitHub](https://github.com/sf1tzp/symbology/discussions).
`;
</script>

<svelte:head>
	<title>FAQ - Symbology</title>
	<meta
		name="description"
		content="Frequently Asked Questions about Symbology Financial Analysis Platform"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Frequently Asked Questions</h1>
		<p class="mx-auto max-w-2xl text-xl text-muted-foreground">
			Everything you need to know about Symbology
		</p>
	</section>

	<!-- FAQ Content -->
	<section class="mx-auto max-w-4xl">
		<Card>
			<CardContent>
				<MarkdownContent {content} />
			</CardContent>
		</Card>
	</section>
</div>
