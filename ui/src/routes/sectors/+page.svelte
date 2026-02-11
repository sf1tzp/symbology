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
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const groups = data.groups || [];

	function handleGroupClick(slug: string) {
		goto(`/sectors/${slug}`);
	}
</script>

<svelte:head>
	<title>Sectors - Symbology</title>
	<meta name="description" content="Explore sector groups and cross-company analysis" />
</svelte:head>

<div class="space-y-8">
	<section class="space-y-4 text-center">
		<h1 class="text-4xl font-bold tracking-tight">Sectors</h1>
		<p class="mx-auto max-w-2xl text-xl text-muted-foreground">
			Explore industry sectors and cross-company analysis
		</p>
	</section>

	{#if groups.length > 0}
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
			{#each groups as group}
				<Card
					class="cursor-pointer transition-shadow hover:shadow-md"
					onclick={() => handleGroupClick(group.slug)}
				>
					<CardHeader>
						<CardTitle class="flex items-center justify-between">
							<span>{group.name}</span>
							<span
								class="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground"
							>
								{group.member_count} companies
							</span>
						</CardTitle>
						{#if group.description}
							<CardDescription>{group.description}</CardDescription>
						{/if}
					</CardHeader>
					<CardContent class="space-y-3">
						{#if group.sic_codes && group.sic_codes.length > 0}
							<div class="flex flex-wrap gap-1">
								{#each group.sic_codes as code}
									<span class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
										SIC {code}
									</span>
								{/each}
							</div>
						{/if}
						{#if group.latest_analysis_summary}
							<p class="line-clamp-3 text-sm text-muted-foreground">
								{group.latest_analysis_summary}
							</p>
						{/if}
						<Button
							variant="outline"
							size="sm"
							class="w-full"
							onclick={() => handleGroupClick(group.slug)}
						>
							View Sector
						</Button>
					</CardContent>
				</Card>
			{/each}
		</div>
	{:else}
		<div class="py-16 text-center">
			<p class="text-lg text-muted-foreground">No sector groups found</p>
			<p class="mt-2 text-sm text-muted-foreground">
				Sector groups can be created via the CLI to organize companies for cross-company analysis.
			</p>
		</div>
	{/if}
</div>
