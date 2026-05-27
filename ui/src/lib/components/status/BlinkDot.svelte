<script lang="ts">
	interface Props {
		color?: string;
	}

	let { color = '#3d8bff' }: Props = $props();
</script>

<span class="blink-dot" style="position: relative; width: 8px; height: 8px; display: inline-block;">
	<span style="position: absolute; inset: 0; border-radius: 999px; background: {color};"></span>
	<span
		class="blink-dot-ring"
		style="position: absolute; inset: -3px; border-radius: 999px; background: {color}; opacity: 0.25;"
	></span>
</span>

<style>
	.blink-dot-ring {
		animation: statusPulse 1.6s ease-out infinite;
	}

	@keyframes statusPulse {
		0% {
			transform: scale(1);
			opacity: 0.45;
		}
		100% {
			transform: scale(2.6);
			opacity: 0;
		}
	}
</style>
