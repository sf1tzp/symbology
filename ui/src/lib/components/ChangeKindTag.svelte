<script lang="ts">
	import { TrendingUp, TrendingDown, TrendingUpDown } from '@lucide/svelte';
	import { changeKindColor } from '$lib/utils/changes';

	// Stylized pill for a change kind — coloured to match the change cards + the
	// per-kind accent palette, with a trend icon. Shared by the diff list rows and
	// the "What's new" cards so a given change kind reads identically everywhere.
	let { changeKind }: { changeKind: string } = $props();
</script>

<span class="tag kind-tag" style="--kind: {changeKindColor(changeKind)};">
	{(changeKind || '').replace('_', '-')}
	{#if changeKind === 'escalated'}
		<TrendingUp class="ml-2 size-3" />
	{:else if changeKind === 'de_emphasised'}
		<TrendingDown class="ml-2 size-3" />
	{:else}
		<TrendingUpDown class="ml-2 size-3" />
	{/if}
</span>

<style>
	.kind-tag {
		background: color-mix(in oklch, var(--kind) 15%, transparent);
		border-color: var(--kind);
		color: var(--kind);
	}
</style>
