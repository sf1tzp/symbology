<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
	import FileText from '@lucide/svelte/icons/file-text';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Calendar from '@lucide/svelte/icons/calendar';

	const features = [
		{
			icon: FileText,
			title: 'Filing Analysis',
			description:
				'Automatically extract and structure key information from SEC filings — 10-Ks, 10-Qs, and more.'
		},
		{
			icon: Sparkles,
			title: 'LLM Insights',
			description:
				'Large language models distill dense filings into structured summaries, risk factors, and key metrics.'
		},
		{
			icon: Calendar,
			title: 'Temporal Comparison',
			description:
				'Track how disclosures, risks, and financials change across quarters and fiscal years.'
		}
	];

	function scrollToGetStarted() {
		document.getElementById('get-started')?.scrollIntoView({ behavior: 'smooth' });
	}
</script>

<!-- Hero -->
<section class="bg-gradient-to-b from-muted/50 to-background py-16 md:py-32">
	<div class="mx-auto max-w-5xl px-4 text-center">
		<h1 class="text-5xl font-bold tracking-tight text-foreground md:text-6xl lg:text-7xl">
			Investment Research,
			<br />
			<span class="text-primary">intelligently automated.</span>
		</h1>
		<p class="mx-auto mt-6 max-w-2xl text-xl text-muted-foreground">
			Every quarter, thousands of public companies file detailed reports with the SEC. Symbology
			uses large language models to read, distill, and compare these filings — so you can focus on
			what actually changed.
		</p>
		<Button size="lg" class="mt-8" onclick={scrollToGetStarted}>Get Started</Button>
	</div>
</section>

<!-- Features -->
<section class="py-16 md:py-24">
	<div class="mx-auto max-w-5xl px-4">
		<div class="grid grid-cols-1 gap-8 md:grid-cols-3">
			{#each features as feature}
				<Card class="text-center">
					<CardContent class="pt-6">
						<div
							class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10"
						>
							<feature.icon class="h-6 w-6 text-primary" />
						</div>
						<h3 class="text-lg font-semibold">{feature.title}</h3>
						<p class="mt-2 text-sm text-muted-foreground">{feature.description}</p>
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
</section>

<!-- Get Started -->
<section id="get-started" class="border-t bg-muted/30 py-16 md:py-24">
	<div class="mx-auto max-w-5xl px-4">
		<h2 class="mb-8 text-center text-3xl font-bold">Explore a Company</h2>
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Select a Company to Get Started</CardTitle>
			</CardHeader>
			<CardContent>
				<CompanySelector showCompanyList={true} />
			</CardContent>
		</Card>
	</div>
</section>
