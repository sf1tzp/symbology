<script lang="ts">
	interface Props {
		kind?: 'ok' | 'warn' | 'err' | 'idle' | 'run';
		size?: number;
	}

	let { kind = 'ok', size = 8 }: Props = $props();

	const colors: Record<string, string> = {
		ok: 'var(--teal-2)',
		warn: 'var(--warn)',
		err: 'var(--danger)',
		idle: 'var(--ink-4)',
		run: '#3d8bff'
	};

	const glowColors: Record<string, string> = {
		ok: 'var(--sage-2)',
		run: 'rgba(61,139,255,0.14)'
	};

	const color = $derived(colors[kind] || colors.idle);
	const glow = $derived(glowColors[kind]);
</script>

<span
	style="display: inline-block; width: {size}px; height: {size}px; border-radius: 999px; background: {color}; box-shadow: {glow
		? `0 0 0 3px ${glow}`
		: 'none'}; flex: 0 0 auto;"
></span>
