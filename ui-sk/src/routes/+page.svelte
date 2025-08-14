<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';

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

<div class="space-y-8">
	<!-- Hero Section -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Symbology</h1>
		<p class="text-muted-foreground mx-auto max-w-2xl text-xl">
			Explore LLM-generated insights from public SEC Filings
		</p>
	</section>

	<!-- Company Search -->
	<section class="mx-auto max-w-2xl">
		<Card>
			<CardHeader>
				<CardTitle>Get Started</CardTitle>
				<CardDescription>
					Search for a company to explore their financial data and analysis
				</CardDescription>
			</CardHeader>
			<CardContent>
				<CompanySelector showCompanyList={true} />
			</CardContent>
		</Card>
	</section>

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
</div>
