<script lang="ts">
	interface Props {
		size?: number;
		class?: string;
	}
	let { size = 24, class: className = '' }: Props = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 64 64"
	fill="none"
	class={className}
	aria-hidden="true"
>
	<path
		d="M32 9 L56 53 L8 53 Z"
		fill="none"
		stroke="currentColor"
		stroke-width="2.75"
		stroke-linejoin="round"
	/>
	<circle cx="32" cy="38" r="5.5" fill="currentColor" />
</svg>
