<script lang="ts">
	interface Props {
		value: number;
		max: number;
		color?: string;
		height?: number;
	}

	let { value, max, color = 'var(--teal-2)', height = 4 }: Props = $props();

	const pct = $derived(Math.min(100, (value / max) * 100));
</script>

<div style="width: 100%; height: {height}px; background: var(--rule); border-radius: 2px;">
	<div style="width: {pct}%; height: 100%; background: {color}; border-radius: 2px;"></div>
</div>
