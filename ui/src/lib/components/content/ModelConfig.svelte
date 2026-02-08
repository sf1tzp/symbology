<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import { Settings, Cpu, Thermometer, FileText } from '@lucide/svelte';
	import type { ModelConfigResponse } from '$lib/api-types';

	let { config }: { config: ModelConfigResponse | null } = $props();

	function formatValue(value: any): string {
		if (value === null || value === undefined) return 'N/A';
		if (typeof value === 'number') {
			if (value >= 1000) {
				return value.toLocaleString();
			}
			return value.toString();
		}
		return String(value);
	}
</script>

{#if config}
	<div class="space-y-4">
		<!-- Model Information -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<Cpu class="h-4 w-4 text-muted-foreground" />
				<span class="font-medium">Model</span>
				<Badge variant="secondary" class="font-mono text-sm">
					{config.model}
				</Badge>
			</div>
		</div>

		<Separator />

		<!-- Model Parameters -->
		<div class="space-y-3">
			<div class="flex items-center space-x-2">
				<Settings class="h-4 w-4 text-muted-foreground" />
				<span class="text-sm font-medium">Parameters</span>
			</div>

			<div class="grid grid-cols-1 gap-3 text-sm">
				{#if config.temperature !== null && config.temperature !== undefined}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<Thermometer class="h-3 w-3 text-muted-foreground" />
							<span class="text-muted-foreground">Temperature</span>
						</div>
						<span class="font-mono">{formatValue(config.temperature)}</span>
					</div>
				{/if}

				{#if config.max_tokens !== null && config.max_tokens !== undefined}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<FileText class="h-3 w-3 text-muted-foreground" />
							<span class="text-muted-foreground">Max Tokens</span>
						</div>
						<span class="font-mono">{formatValue(config.max_tokens)}</span>
					</div>
				{/if}

				{#if config.top_p !== null && config.top_p !== undefined}
					<div class="flex items-center justify-between">
						<span class="text-muted-foreground">Top P</span>
						<span class="font-mono">{formatValue(config.top_p)}</span>
					</div>
				{/if}

				{#if config.top_k !== null && config.top_k !== undefined}
					<div class="flex items-center justify-between">
						<span class="text-muted-foreground">Top K</span>
						<span class="font-mono">{formatValue(config.top_k)}</span>
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center p-6">
		<div class="text-center">
			<Settings class="mx-auto h-8 w-8 text-muted-foreground" />
			<p class="mt-2 text-sm text-muted-foreground">No model configuration available</p>
		</div>
	</div>
{/if}
