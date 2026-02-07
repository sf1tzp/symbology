<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const group = data.group;
	const analyses = data.analyses || [];

	function handleCompanyClick(ticker: string) {
		goto(`/c/${ticker}`);
	}

	function formatDate(dateString: string): string {
		try {
			return new Date(dateString).toLocaleDateString();
		} catch {
			return dateString;
		}
	}
</script>

<svelte:head>
	<title>{group?.name || data.slug} - Sectors - Symbology</title>
	<meta
		name="description"
		content="Sector analysis for {group?.name || data.slug}"
	/>
</svelte:head>

<div class="space-y-8">
	<!-- Header with back navigation -->
	<div class="space-y-4">
		<Button variant="ghost" onclick={() => goto('/sectors')}>← Back to Sectors</Button>

		{#if !group}
			<div class="rounded-md bg-red-50 p-4 text-red-700">
				<p class="font-medium">Sector group not found: {data.slug}</p>
			</div>
		{:else}
			<div class="space-y-2">
				<div class="flex items-center space-x-3">
					<h1 class="text-4xl font-bold">{group.name}</h1>
					<span
						class="rounded-full bg-primary px-3 py-1 text-sm font-medium text-primary-foreground"
					>
						{group.member_count} companies
					</span>
				</div>
				{#if group.description}
					<p class="text-lg text-muted-foreground">{group.description}</p>
				{/if}
				{#if group.sic_codes && group.sic_codes.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each group.sic_codes as code}
							<span
								class="rounded bg-muted px-2 py-1 text-sm text-muted-foreground"
							>
								SIC {code}
							</span>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	{#if group}
		<!-- Member Companies -->
		<Card>
			<CardHeader>
				<CardTitle>Member Companies</CardTitle>
				<CardDescription>
					Companies in this sector group
				</CardDescription>
			</CardHeader>
			<CardContent>
				{#if group.companies && group.companies.length > 0}
					<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
						{#each group.companies as company}
							<Card
								class="cursor-pointer transition-shadow hover:bg-muted/50 hover:shadow-md"
								onclick={() => handleCompanyClick(company.ticker)}
							>
								<CardContent>
									<div class="flex items-center justify-between">
										<div>
											<div class="font-medium">
												{company.display_name || company.name}
											</div>
											<div class="text-sm text-muted-foreground">
												{company.ticker}
												{#if company.sic_description}
													&middot; {company.sic_description}
												{/if}
											</div>
										</div>
										<Button
											variant="outline"
											size="sm"
											onclick={() => handleCompanyClick(company.ticker)}
										>
											View
										</Button>
									</div>
								</CardContent>
							</Card>
						{/each}
					</div>
				{:else}
					<p class="py-8 text-center text-muted-foreground">
						No companies in this group yet. Use the CLI to add companies.
					</p>
				{/if}
			</CardContent>
		</Card>

		<!-- Sector Analysis -->
		<Card>
			<CardHeader>
				<CardTitle>Sector Analysis</CardTitle>
				<CardDescription>
					Cross-company analysis generated from aggregate summaries
				</CardDescription>
			</CardHeader>
			<CardContent>
				{#if analyses.length > 0}
					<div class="space-y-6">
						{#each analyses as analysis}
							<div class="space-y-2">
								<div class="text-xs text-muted-foreground">
									Generated on {formatDate(analysis.created_at)}
								</div>
								{#if analysis.content}
									<MarkdownContent content={analysis.content} />
								{/if}
							</div>
							{#if analyses.length > 1}
								<hr class="border-border" />
							{/if}
						{/each}
					</div>
				{:else}
					<div class="py-8 text-center">
						<p class="text-muted-foreground">No sector analysis available yet</p>
						<p class="mt-2 text-sm text-muted-foreground">
							Trigger a sector analysis via the CLI to generate cross-company insights.
						</p>
					</div>
				{/if}
			</CardContent>
		</Card>
	{/if}
</div>
