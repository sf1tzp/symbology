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
	import type { CompanyResponse } from '$lib/generated-api-types';

	function handleCompanySelected(event: CustomEvent<CompanyResponse>) {
		const company = event.detail;
		// Navigation is handled by the CompanySelector component
		console.log('Company selected:', company);
	}

	function handleCompanyClick(ticker: string) {
		goto(`/c/${ticker}`);
	}
</script>

<svelte:head>
	<title>Companies - Symbology</title>
	<meta
		name="description"
		content="Browse and explore public company profiles and financial data"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Header -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Companies</h1>
		<p class="mx-auto max-w-2xl text-xl text-muted-foreground">
			Browse and explore public company profiles, financial data, and analysis
		</p>
	</section>

	<!-- Search Section -->
	<section class="mx-auto max-w-4xl">
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Search Companies</CardTitle>
				<CardDescription>
					Search by company name or ticker symbol to explore their financial data
				</CardDescription>
			</CardHeader>
			<CardContent>
				<CompanySelector
					on:companySelected={handleCompanySelected}
					showCompanyList={true}
					variant="default"
				/>
			</CardContent>
		</Card>
	</section>

	<!-- Browse by Sector -->
	<!-- <section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">Browse by Sector</h2>
			<p class="text-muted-foreground mt-2">Explore companies organized by industry sectors</p>
		</div>

		<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
			{#each ['Technology', 'Healthcare', 'Financial', 'Energy', 'Consumer', 'Industrial', 'Materials', 'Utilities'] as sector}
				<Card class="cursor-pointer transition-shadow hover:shadow-md">
					<CardContent class="pt-6">
						<div class="text-center">
							<h3 class="font-medium">{sector}</h3>
							<p class="text-muted-foreground mt-1 text-sm">Coming Soon</p>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>
	</section> -->
</div>
