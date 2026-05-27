<script lang="ts">
	import BlinkDot from './BlinkDot.svelte';

	interface Props {
		active?: string;
		refreshAgo?: string;
	}

	let { active = 'Overview', refreshAgo = 'just now' }: Props = $props();

	const items = ['Overview', 'Ingestion', 'Generations', 'Queue', 'Workers'];

	const anchors: Record<string, string> = {
		Overview: '#',
		Ingestion: '#ingestion',
		Generations: '#generations',
		Queue: '#queue',
		Workers: '#workers'
	};
</script>

<div class="status-nav">
	{#each items as item (item)}
		<a href={anchors[item] ?? '#'} class="status-nav-item" class:active={item === active}>
			{item}
		</a>
	{/each}
	<span class="status-nav-live">
		<BlinkDot color="var(--teal-2)" />
		<span class="meta">Live &middot; refreshed {refreshAgo}</span>
	</span>
</div>

<style>
	.status-nav {
		margin-bottom: 0.75rem;
		padding: 1rem 0 0.875rem;
		border-bottom: 1px solid var(--rule);
		display: flex;
		align-items: center;
		gap: 1.75rem;
	}
	.status-nav-item {
		font-size: 0.84375rem;
		color: var(--ink-3);
		text-decoration: none;
		border-bottom: 2px solid transparent;
		padding-bottom: 0.875rem;
		margin-bottom: -0.9375rem;
	}
	.status-nav-item.active {
		color: var(--ink);
		border-bottom-color: var(--ink);
	}
	.status-nav-live {
		margin-left: auto;
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
	}
</style>
