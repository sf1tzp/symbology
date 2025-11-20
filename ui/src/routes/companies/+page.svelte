<script lang="ts">
	import { Card, CardContent } from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
</script>

<svelte:head>
	<title>Symbology - Company Search</title>
	<meta name="description" content="Browse and explore public companies" />
</svelte:head>

<div class="space-y-8">
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Search Companies</h1>
		<p class="mx-auto max-w-2xl text-xl text-muted-foreground">
			Browse and company profiles, financial data, and analysis
		</p>
	</section>

	<section class="mx-auto max-w-4xl">
		<Card>
			<CardContent>
				<CompanySelector showCompanyList={true} />
			</CardContent>
		</Card>
	</section>
</div>
