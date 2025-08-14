<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Separator } from '$lib/components/ui/separator';
	import { Settings, Cpu, Thermometer, Target, Hash, Dice6, Gpu, FileText } from '@lucide/svelte';
	import type { ModelConfigResponse } from '$lib/generated-api-types';

	let { config }: { config: ModelConfigResponse | null } = $props();

	function formatValue(value: any): string {
		if (value === null || value === undefined) return 'N/A';
		if (typeof value === 'number') {
			// Format large numbers with commas
			if (value >= 1000) {
				return value.toLocaleString();
			}
			return value.toString();
		}
		return String(value);
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getModelDisplayName(name: string): string {
		// Convert model names to more readable format

		// FIXME: When the test db was populated with modelConfigs, they were given a custom names instead of using only the model name here
		//return name.replace(/[_:]/g, ' ').toUpperCase();
		// We'll hack around this for now by only showing the first part
		const parts = name.split('_');
		return parts[0];
	}
</script>

{#if config}
	<div class="space-y-4">
		<!-- Model Information -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<Cpu class="text-muted-foreground h-4 w-4" />
				<span class="font-medium">Model</span>
				<Badge variant="secondary" class="font-mono text-sm">
					{getModelDisplayName(config.name)}
				</Badge>
			</div>
		</div>

		<Separator />

		<!-- Model Parameters -->
		<div class="space-y-3">
			<div class="flex items-center space-x-2">
				<Settings class="text-muted-foreground h-4 w-4" />
				<span class="text-sm font-medium">Parameters</span>
			</div>

			<div class="grid grid-cols-1 gap-3 text-sm">
				{#if config.temperature !== null}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Thermometer class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">Temperature</span>
						</div>
						<span class="font-mono">{formatValue(config.temperature)}</span>
					</div>
				{/if}

				<!-- {#if config.top_p !== null}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Target class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">Top-p</span>
						</div>
						<span class="font-mono">{formatValue(config.top_p)}</span>
					</div>
				{/if}

				{#if config.top_k !== null}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Hash class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">Top-k</span>
						</div>
						<span class="font-mono">{formatValue(config.top_k)}</span>
					</div>
				{/if} -->

				{#if config.num_ctx !== null}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<FileText class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">Context Window</span>
						</div>
						<span class="font-mono">{formatValue(config.num_ctx)}</span>
					</div>
				{/if}

				{#if config.seed !== null}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Dice6 class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">Seed</span>
						</div>
						<span class="font-mono text-xs">{formatValue(config.seed)}</span>
					</div>
				{/if}

				{#if config.num_gpu !== null && config.num_gpu > 0}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Gpu class="text-muted-foreground h-3 w-3" />
							<span class="text-muted-foreground">GPUs</span>
						</div>
						<span class="font-mono">{formatValue(config.num_gpu)}</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- <Separator /> -->

		<!-- Metadata -->
		<!-- <div class="space-y-1">
			<p class="text-muted-foreground text-xs">
				Created {formatDate(config.created_at)}
			</p>
			<p class="text-muted-foreground font-mono text-xs">
				ID: {config.id.substring(0, 8)}...
			</p>
		</div> -->
	</div>
{:else}
	<div class="flex items-center justify-center p-6">
		<div class="text-center">
			<Settings class="text-muted-foreground mx-auto h-8 w-8" />
			<p class="text-muted-foreground mt-2 text-sm">No model configuration available</p>
		</div>
	</div>
{/if}
