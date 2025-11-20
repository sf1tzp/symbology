<script lang="ts">
	import { Card, CardContent } from '$lib/components/ui/card';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let content=`
## What's symbology?

Symbology is the study of symbols.

Stock tickers are sometimes referred to as symbols, so symbolgy.online aims to make the study of symbols easier for everyone.

## How's it work?

The short answer is: We use LLMs to compare years of financial reporting and summarize the contents within.

### A slightly longer answer

Filings are retrieved from the S.E.C. by utilizing the amazing [edgartools library](https://github.com/dgunning/edgartools). These filings are comprised of various sections, which can be quite tedious and lengthy reads on their own (Several thousand lines of unstructured plaintext with all manner of formatting inconsistencies).

Leveraging [ollama](https://ollama.com), we try to condense these sections down while producing a consistent output format. By repeating this process year after year, we're able to use the LLM to summarize changes in those sections over time.

## Why?

By combining structured, "hands off" inference with long-term observation and summarization, we hope to produce a trustworthy resource for research automatically - without involving 3rd parties.

S.E.C. Filings are a great dataset to practice with:
- Many participating companies
- New data released at regular intervals
- Reporting guidelines make correlation possible, though difficult to do programatically without some form of [NLP](https://en.wikipedia.org/wiki/Natural_language_processing).


#### _Questions unanswered?_ Start a discussion [on github](https://github.com/sf1tzp/symbology/discussions)
`
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
				<MarkdownContent content={content}/>
			</CardContent>
		</Card>
	</section>
</div>
