<script lang="ts">
	interface DataPoint {
		label: string;
		v: number;
	}

	interface Props {
		data: DataPoint[];
		height?: number;
		color?: string;
		formatY?: (v: number) => string | number;
	}

	let { data, height = 160, color = 'var(--teal-2)', formatY = (v: number) => v }: Props = $props();

	const W = 720;
	const padL = 38;
	const padR = 8;
	const padT = 8;
	const padB = 24;

	const innerW = $derived(W - padL - padR);
	const innerH = $derived(height - padT - padB);
	const max = $derived(Math.max(...data.map((d) => d.v)) * 1.15 || 1);
	const stepX = $derived(data.length > 1 ? innerW / (data.length - 1) : innerW);
	const pts = $derived(
		data.map((d, i) => [padL + i * stepX, padT + innerH - (d.v / max) * innerH])
	);
	const line = $derived(
		pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
	);
	const area = $derived(
		pts.length > 0
			? `${line} L${pts[pts.length - 1][0]},${padT + innerH} L${pts[0][0]},${padT + innerH} Z`
			: ''
	);
	const ticks = 3;
	const tickVals = $derived(Array.from({ length: ticks + 1 }, (_, i) => (max * i) / ticks));
	const labelStep = $derived(Math.ceil(data.length / 8));
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
			<text x={padL - 8} y={y + 3} text-anchor="end">{formatY(Math.round(v))}</text>
		{/each}
		{#each data as d, i (i)}
			{#if i % labelStep === 0 || i === data.length - 1}
				<text x={padL + i * stepX} y={height - 8} text-anchor="middle">{d.label}</text>
			{/if}
		{/each}
	</g>
	{#if area}
		<path d={area} fill={color} fill-opacity="0.14" />
		<path d={line} fill="none" stroke={color} stroke-width="1.6" stroke-linejoin="round" />
	{/if}
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
