<script lang="ts">
	import { Card, CardContent } from '$lib/components/ui/card';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
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
				<MarkdownContent
					content={`
## What is this website about?

This website provides a new way to understand company activities. We use Large Language Models (LLMs) to analyze the disclosures companies are required to make by the SEC. These filings – often lengthy and dense – offer a uniquely valuable, primary source perspective on a company's strategy, operations, and risks.  We believe these documents contain incredibly insightful information, but the required format and legal language makes them difficult to digest.  We aim to make this information accessible.


## Why are these filings so verbose?

The Securities Exchange Act and related regulations mandate extensive disclosures. While designed to be transparent, these requirements often lead to filings that are long, repetitive, and filled with legal jargon. This is a consequence of the law itself and isn't necessarily a reflection of the company's intent.


## How does your website work?

We're leveraging the power of LLMs to tackle this challenge.  Our process is layered:

- What Happened: We begin by extracting and summarizing the core events and information directly from the source filings. This provides a clear understanding of the company's reported activities.
- Changes Over Time: We then analyze these filings sequentially to identify changes in company strategy, operations, and disclosures.  This highlights trends and potential shifts that might otherwise be missed.


## Do you offer investment advice or opinions?

No, absolutely not. Our sole purpose is to provide accurate and concise summaries of publicly available information. We do not make any judgments, offer investment recommendations, or express opinions about a company's value or prospects. We are purely a data-driven summarization service.


## Is this website open source? How can I reproduce the content?

Yes! This entire website and all its content are open source. We believe in transparency and reproducibility. You can reproduce any piece of written content here, provided you have access to Ollama and enough resources to meet the provided model configuration.  We will be publishing these configurations and prompt details for all our generations.


## How can I track the source material?

Each generated piece of content is linked to its original source documents.  You can also follow the "chain of generation," seeing exactly how the analysis, summary, and source document are connected. Each content item also has a unique "short sha" identifier for easy linkability and sharing.


## How can I support the project?

Star us on GitHub! https://github.com/sf1tzp/symbology  - This helps us gain visibility and demonstrates community interest.

Report issues: If you spot any errors or have suggestions for improvement, please open an issue on our GitHub repository. We welcome your feedback!

Spread the word: Share our website with others who might find it valuable!


## What are your plans for the future?

We're excited about the potential of this project and have several enhancements planned:

- More Frequent Filing Analysis:  We aim to provide analysis on a quarterly basis, keeping pace with company disclosures.
- Financial Standings Integration: Incorporating financial data alongside the textual analysis.
- Improved User Interface: Designing a more intuitive interface to fully document the prompts, configurations, and models used in content generation.
- Prompt & Config Documentation: Provide full transparency on how we are generating content.
- Reproducibility: Share our full model config for others to build upon.


## How was this website initially created?

The initial content was generated at home using an inexpsensive consumer GPU. Due to limited VRAM, our intial analysis have been dialed back in scope, but we're still impressed by the results.

We are currently exploring options for renting higher-tier GPUs to improve the fidelity of our LLM configurations and accelerate content generation.
					`}
				/>
			</CardContent>
		</Card>
	</section>
</div>
