<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	// Mock type for now - will be replaced with real API types
	interface CompanyResponse {
		id: string;
		name: string;
		tickers: string[];
		sector?: string;
		description?: string;
	}

	function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
		const company = event.detail;
		// Navigation is handled by the CompanySelector component
		// but we could add additional logic here if needed
		console.log('Company selected:', company);
	}
</script>

<svelte:head>
	<title>Symbology - Financial Analysis Platform</title>
	<meta name="description" content="Explore LLM-generated insights on publicly traded companies." />
</svelte:head>

<!-- Mobile/Tablet Layout -->
<div class="space-y-8 lg:hidden">
	<!-- Hero Section -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Symbology</h1>
		<p class="mx-auto max-w-2xl text-xl text-muted-foreground">
			Explore LLM-generated insights from public SEC Filings
		</p>
		<div class="mx-auto max-w-2xl">
			<Card>
				<CardContent>
					<MarkdownContent
						content={`
> The Securities Exchange Act of 1933 was written in the spirit of full disclosure.

> But wading through the verbose filings can be a challenge. We leverage the power of Large Language Models (LLMs) to distill these primary source documents into clear, concise summaries, revealing what companies are up to, and how that's changing over time. Explore company activity directly from the source - completely open source and easily shareable.  Learn more in our [FAQ](https://symbology.online/faq), or leave us a star on [GitHub](https://github.com/sf1tzp/symbology)
						`}
					/>
				</CardContent>
			</Card>
		</div>
	</section>

	<!-- Company Search -->
	<section class="mx-auto max-w-2xl">
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Get Started</CardTitle>
				<CardDescription>
					Search for a company to explore their financial data and analysis
				</CardDescription>
			</CardHeader>
			<CardContent>
				<CompanySelector showCompanyList={true} />
			</CardContent>
		</Card>
	</section>
</div>

<!-- Large Device Layout -->
<div class="hidden lg:block">
	<div class="grid min-h-[calc(100vh-12rem)] grid-cols-12 gap-6">
		<!-- Hero Section - 4 Columns -->
		<div class="col-span-4 space-y-6">
			<section class="space-y-4 text-center">
				<h1 class="text-5xl font-bold tracking-tight">Symbology</h1>
				<p class="text-xl text-muted-foreground">
					Explore LLM-generated insights from public SEC Filings
				</p>
				<Card>
					<CardContent class="p-6">
						<MarkdownContent
							content={`
> The Securities Exchange Act of 1933 was written in the spirit of full disclosure. _- [Wikipedia](https://en.wikipedia.org/wiki/Securities_Act_of_1933)_

But full disclosure is extremely verbose.

We leverage the power of Large Language Models to distill primary source documents from the [SEC](https://sec.gov) into clear, concise summaries. revealing what companies are up to, and how that's changing over time. Explore company activity directly from the source - completely open source and easily shareable.  Learn more in our [FAQ](https://symbology.online/faq), or leave us a star on [GitHub](https://github.com/sf1tzp/symbology).
							`}
						/>
					</CardContent>
				</Card>
			</section>
		</div>

		<!-- Company Selector - 7 Columns -->
		<div class="col-span-8 space-y-6">
			<section>
				<Card class="h-full">
					<CardHeader>
						<CardTitle class="text-xl">Get Started</CardTitle>
						<CardDescription>
							Search for a company to explore their financial data and analysis
						</CardDescription>
					</CardHeader>
					<CardContent class="p-6">
						<CompanySelector showCompanyList={true} />
					</CardContent>
				</Card>
			</section>
		</div>
	</div>
</div>

<!-- Quick Navigation -->
<!-- <section class="mx-auto grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-3">
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Companies</CardTitle>
				<CardDescription>Browse company profiles and financial overviews</CardDescription>
			</CardHeader>
		</Card>

		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Generated Content</CardTitle>
				<CardDescription>View LLM-generated analysis and insights</CardDescription>
			</CardHeader>
		</Card>

		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Filings</CardTitle>
				<CardDescription>Explore SEC filings and documents</CardDescription>
			</CardHeader>
		</Card>
	</section> -->
