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
	import { Input } from '$lib/components/ui/input';

	let searchTerm = $state('');
	let isSearching = $state(false);

	// Mock recent filings data
	const recentFilings = [
		{
			company: 'Apple Inc.',
			ticker: 'AAPL',
			filingType: '10-K',
			filingDate: '2024-10-30',
			period: 'FY 2024',
			edgarId: '0000320193-24-000123'
		},
		{
			company: 'Microsoft Corporation',
			ticker: 'MSFT',
			filingType: '10-Q',
			filingDate: '2024-10-24',
			period: 'Q1 2025',
			edgarId: '0000789019-24-000089'
		},
		{
			company: 'Tesla, Inc.',
			ticker: 'TSLA',
			filingType: '8-K',
			filingDate: '2024-10-20',
			period: 'Current Report',
			edgarId: '0001318605-24-000156'
		},
		{
			company: 'Alphabet Inc.',
			ticker: 'GOOGL',
			filingType: '10-Q',
			filingDate: '2024-10-29',
			period: 'Q3 2024',
			edgarId: '0001652044-24-000091'
		}
	];

	const filingTypes = [
		{ type: '10-K', description: 'Annual Report', frequency: 'Annual' },
		{ type: '10-Q', description: 'Quarterly Report', frequency: 'Quarterly' },
		{ type: '8-K', description: 'Current Report', frequency: 'As Needed' },
		{ type: 'DEF 14A', description: 'Proxy Statement', frequency: 'Annual' },
		{ type: '13F', description: 'Holdings Report', frequency: 'Quarterly' },
		{ type: 'S-1', description: 'Registration Statement', frequency: 'As Needed' }
	];

	function handleFilingClick(edgarId: string) {
		goto(`/f/${edgarId}`);
	}

	function handleCompanyClick(ticker: string) {
		goto(`/c/${ticker}`);
	}

	function handleSearch() {
		if (searchTerm.trim()) {
			isSearching = true;
			// Simulate search - in real app this would be an API call
			setTimeout(() => {
				isSearching = false;
				// For now, just show a placeholder
			}, 500);
		}
	}

	function getFilingTypeVariant(type: string) {
		switch (type) {
			case '10-K':
				return 'default';
			case '10-Q':
				return 'secondary';
			case '8-K':
				return 'outline';
			default:
				return 'outline';
		}
	}
</script>

<svelte:head>
	<title>SEC Filings - Symbology</title>
	<meta
		name="description"
		content="Browse and explore SEC filings, 10-K, 10-Q, and other regulatory documents"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Header -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">SEC Filings</h1>
		<p class="text-muted-foreground mx-auto max-w-2xl text-xl">
			Browse and explore SEC filings, regulatory documents, and corporate disclosures
		</p>
	</section>

	<!-- Search Section -->
	<section class="mx-auto max-w-2xl">
		<Card>
			<CardHeader>
				<CardTitle>Search Filings</CardTitle>
				<CardDescription>
					Search by company, filing type, or EDGAR ID to find specific documents
				</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				<div class="flex space-x-2">
					<Input
						placeholder="Search by company, filing type, or EDGAR ID"
						bind:value={searchTerm}
						onkeydown={(e) => e.key === 'Enter' && handleSearch()}
						class="flex-1"
					/>
					<Button onclick={handleSearch} disabled={isSearching || !searchTerm.trim()}>
						{#if isSearching}
							Searching...
						{:else}
							Search
						{/if}
					</Button>
				</div>
			</CardContent>
		</Card>
	</section>

	<!-- Recent Filings -->
	<section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">Recent Filings</h2>
			<p class="text-muted-foreground mt-2">Latest SEC filings from major companies</p>
		</div>

		<div class="space-y-4">
			{#each recentFilings as filing}
				<Card class="cursor-pointer transition-shadow hover:shadow-md">
					<CardHeader>
						<div class="flex items-start justify-between">
							<div class="space-y-2">
								<div class="flex items-center space-x-2">
									<CardTitle class="text-lg">{filing.company}</CardTitle>
									<Button
										variant="link"
										class="h-auto p-0 font-medium text-blue-600"
										onclick={() => handleCompanyClick(filing.ticker)}
									>
										{filing.ticker}
									</Button>
								</div>
								<div class="flex items-center space-x-2">
									<span
										class="rounded-full px-2 py-1 text-xs font-medium {getFilingTypeVariant(
											filing.filingType
										) === 'default'
											? 'bg-primary text-primary-foreground'
											: getFilingTypeVariant(filing.filingType) === 'secondary'
												? 'bg-secondary text-secondary-foreground'
												: 'bg-muted text-muted-foreground'}"
									>
										{filing.filingType}
									</span>
									<span class="text-muted-foreground text-sm">{filing.period}</span>
								</div>
							</div>
							<div class="text-muted-foreground text-right text-sm">
								{filing.filingDate}
							</div>
						</div>
					</CardHeader>
					<CardContent>
						<Button
							variant="outline"
							class="w-full"
							onclick={() => handleFilingClick(filing.edgarId)}
						>
							View Filing
						</Button>
					</CardContent>
				</Card>
			{/each}
		</div>
	</section>

	<!-- Filing Types -->
	<section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">Filing Types</h2>
			<p class="text-muted-foreground mt-2">Understanding different types of SEC filings</p>
		</div>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each filingTypes as filingType}
				<Card>
					<CardHeader>
						<div class="flex items-center justify-between">
							<CardTitle class="text-lg">{filingType.type}</CardTitle>
							<span
								class="bg-muted text-muted-foreground rounded-full px-2 py-1 text-xs font-medium"
							>
								{filingType.frequency}
							</span>
						</div>
						<CardDescription>{filingType.description}</CardDescription>
					</CardHeader>
					<CardContent>
						<p class="text-muted-foreground text-sm">
							Learn more about {filingType.type} filings and their contents
						</p>
					</CardContent>
				</Card>
			{/each}
		</div>
	</section>
</div>
