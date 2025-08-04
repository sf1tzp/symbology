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

	// Mock generated content data
	const featuredAnalysis = [
		{
			title: 'Apple Q4 2024 Financial Analysis',
			company: 'Apple Inc.',
			ticker: 'AAPL',
			type: 'Financial Summary',
			model: 'GPT-4',
			createdDate: '2024-11-01',
			sha: 'a1b2c3d4e5f6',
			description: "Comprehensive analysis of Apple's Q4 2024 earnings and financial performance"
		},
		{
			title: 'Tesla Risk Factor Analysis',
			company: 'Tesla, Inc.',
			ticker: 'TSLA',
			type: 'Risk Assessment',
			model: 'Claude-3',
			createdDate: '2024-10-28',
			sha: 'b2c3d4e5f6g7',
			description: "AI-generated analysis of Tesla's key business risks and market challenges"
		},
		{
			title: 'Microsoft Cloud Revenue Trends',
			company: 'Microsoft Corporation',
			ticker: 'MSFT',
			type: 'Revenue Analysis',
			model: 'GPT-4',
			createdDate: '2024-10-25',
			sha: 'c3d4e5f6g7h8',
			description: "Deep dive into Microsoft's cloud business growth and revenue patterns"
		},
		{
			title: 'Meta AI Investment Strategy',
			company: 'Meta Platforms, Inc.',
			ticker: 'META',
			type: 'Strategic Analysis',
			model: 'Claude-3',
			createdDate: '2024-10-20',
			sha: 'd4e5f6g7h8i9',
			description: "Analysis of Meta's artificial intelligence investments and strategic direction"
		}
	];

	const analysisTypes = [
		{
			type: 'Financial Summary',
			description: 'Comprehensive financial performance analysis',
			icon: '📊',
			count: 45
		},
		{
			type: 'Risk Assessment',
			description: 'Business risks and market challenges evaluation',
			icon: '⚠️',
			count: 23
		},
		{
			type: 'Revenue Analysis',
			description: 'Revenue trends and growth pattern insights',
			icon: '💰',
			count: 31
		},
		{
			type: 'Strategic Analysis',
			description: 'Business strategy and competitive positioning',
			icon: '🎯',
			count: 18
		},
		{
			type: 'Market Analysis',
			description: 'Industry trends and market opportunity assessment',
			icon: '📈',
			count: 27
		},
		{
			type: 'ESG Analysis',
			description: 'Environmental, social, and governance evaluation',
			icon: '🌱',
			count: 12
		}
	];

	function handleAnalysisClick(ticker: string, sha: string) {
		goto(`/g/${ticker}/${sha}`);
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

	function getTypeColor(type: string) {
		const colors = {
			'Financial Summary': 'bg-blue-100 text-blue-800',
			'Risk Assessment': 'bg-red-100 text-red-800',
			'Revenue Analysis': 'bg-green-100 text-green-800',
			'Strategic Analysis': 'bg-purple-100 text-purple-800'
		};
		return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
	}
</script>

<svelte:head>
	<title>AI Analysis - Symbology</title>
	<meta
		name="description"
		content="Browse AI-generated financial analysis, insights, and reports for public companies"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Header -->
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">AI Analysis</h1>
		<p class="text-muted-foreground mx-auto max-w-2xl text-xl">
			Explore AI-generated financial analysis, insights, and reports for public companies
		</p>
	</section>

	<!-- Search Section -->
	<section class="mx-auto max-w-2xl">
		<Card>
			<CardHeader>
				<CardTitle>Search Analysis</CardTitle>
				<CardDescription>
					Search by company, analysis type, or keywords to find specific insights
				</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				<div class="flex space-x-2">
					<Input
						placeholder="Search by company, analysis type, or keywords"
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

	<!-- Featured Analysis -->
	<section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">Recent Analysis</h2>
			<p class="text-muted-foreground mt-2">Latest AI-generated insights and analysis reports</p>
		</div>

		<div class="space-y-4">
			{#each featuredAnalysis as analysis}
				<Card class="cursor-pointer transition-shadow hover:shadow-md">
					<CardHeader>
						<div class="flex items-start justify-between">
							<div class="flex-1 space-y-2">
								<CardTitle class="text-lg">{analysis.title}</CardTitle>
								<div class="flex items-center space-x-2">
									<Button
										variant="link"
										class="h-auto p-0 font-medium text-blue-600"
										onclick={() => handleCompanyClick(analysis.ticker)}
									>
										{analysis.company} ({analysis.ticker})
									</Button>
								</div>
								<div class="flex items-center space-x-2">
									<span class="rounded-full px-2 py-1 text-xs {getTypeColor(analysis.type)}">
										{analysis.type}
									</span>
									<span class="text-muted-foreground text-sm">Generated by {analysis.model}</span>
								</div>
								<CardDescription>{analysis.description}</CardDescription>
							</div>
							<div class="text-muted-foreground text-right text-sm">
								{analysis.createdDate}
							</div>
						</div>
					</CardHeader>
					<CardContent>
						<Button
							variant="outline"
							class="w-full"
							onclick={() => handleAnalysisClick(analysis.ticker, analysis.sha)}
						>
							View Analysis
						</Button>
					</CardContent>
				</Card>
			{/each}
		</div>
	</section>

	<!-- Analysis Types -->
	<section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">Analysis Categories</h2>
			<p class="text-muted-foreground mt-2">
				Explore different types of AI-generated financial analysis
			</p>
		</div>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each analysisTypes as category}
				<Card class="cursor-pointer transition-shadow hover:shadow-md">
					<CardHeader>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-3">
								<span class="text-2xl">{category.icon}</span>
								<div>
									<CardTitle class="text-lg">{category.type}</CardTitle>
									<CardDescription class="text-sm">{category.count} reports</CardDescription>
								</div>
							</div>
						</div>
					</CardHeader>
					<CardContent>
						<p class="text-muted-foreground text-sm">
							{category.description}
						</p>
					</CardContent>
				</Card>
			{/each}
		</div>
	</section>

	<!-- AI Models -->
	<section class="space-y-6">
		<div class="text-center">
			<h2 class="text-2xl font-semibold">AI Models</h2>
			<p class="text-muted-foreground mt-2">Analysis powered by leading AI models</p>
		</div>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
			<Card>
				<CardHeader>
					<CardTitle class="text-lg">GPT-4</CardTitle>
					<CardDescription>OpenAI's advanced language model</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="text-muted-foreground text-sm">
						Comprehensive analysis with deep financial reasoning
					</p>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Claude-3</CardTitle>
					<CardDescription>Anthropic's constitutional AI model</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="text-muted-foreground text-sm">Balanced analysis with ethical AI principles</p>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="text-lg">Custom Models</CardTitle>
					<CardDescription>Specialized financial analysis models</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="text-muted-foreground text-sm">
						Domain-specific models trained on financial data
					</p>
				</CardContent>
			</Card>
		</div>
	</section>
</div>
