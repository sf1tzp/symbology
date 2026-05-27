<script lang="ts">
	interface Props {
		data: Record<string, unknown>[];
		segments: string[];
		colors: string[];
		height?: number;
	}

	let { data, segments, colors, height = 200 }: Props = $props();

	const W = 720;
	const padL = 38;
	const padR = 8;
	const padT = 8;
	const padB = 24;

	const innerW = $derived(W - padL - padR);
	const innerH = $derived(height - padT - padB);
	const max = $derived(
		Math.max(...data.map((d) => segments.reduce((s, k) => s + ((d[k] as number) || 0), 0))) * 1.1
	);
	const groupW = $derived(innerW / data.length);
	const barW = $derived(Math.min(20, groupW * 0.62));
	const ticks = 4;
	const tickVals = $derived(Array.from({ length: ticks + 1 }, (_, i) => (max * i) / ticks));
</script>

<svg class="chart-svg" viewBox="0 0 {W} {height}" preserveAspectRatio="xMidYMid meet">
	<g class="chart-grid">
		{#each tickVals as v, i (i)}
			{@const y = padT + innerH - (v / max) * innerH}
			<line x1={padL} x2={W - padR} y1={y} y2={y} />
		{/each}
	</g>
	<g class="chart-axis">
		{#each tickVals as v, i (i)}
			{@const y = padT + innerH - (v / max) * innerH}
			<text x={padL - 8} y={y + 3} text-anchor="end">{Math.round(v)}</text>
		{/each}
	</g>
	{#each data as d, i (i)}
		{@const cx = padL + i * groupW + groupW / 2}
		{#snippet bars()}
			{@const vals = segments.map((seg) => (d[seg] as number) || 0)}
			{#each segments as seg, si (seg)}
				{@const v = vals[si]}
				{@const h = (v / max) * innerH}
				{@const cum = vals.slice(0, si).reduce((a, b) => a + (b / max) * innerH, 0)}
				{@const y = padT + innerH - cum - h}
				<rect
					x={cx - barW / 2}
					{y}
					width={barW}
					height={Math.max(0, h - 0.5)}
					fill={colors[si]}
					rx={si === segments.length - 1 ? 2 : 0}
				/>
			{/each}
		{/snippet}
		<g>
			{@render bars()}
			{#if i % 2 === 0 || i === data.length - 1}
				<text
					x={cx}
					y={height - 8}
					text-anchor="middle"
					font-family="var(--mono)"
					font-size="10"
					fill="var(--ink-4)"
				>
					{d.label}
				</text>
			{/if}
		</g>
	{/each}
</svg>

<style>
	.chart-svg {
		width: 100%;
		height: auto;
	}
	.chart-grid line {
		stroke: var(--rule);
		stroke-width: 1;
	}
	.chart-axis text {
		font-family: var(--mono);
		font-size: 10px;
		fill: var(--ink-4);
	}
</style>
