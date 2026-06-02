<script lang="ts">
	import { CircleQuestionMark } from '@lucide/svelte';

	let { size = 10 }: { size?: number } = $props();
</script>

<a
	href="/faq#synthesis-levels"
	class="synthesis-help"
	title="What are synthesis levels?"
	aria-label="What are synthesis levels?"
>
	<CircleQuestionMark style="width: {size}px; height: {size}px;" />
</a>

<style>
	.synthesis-help {
		display: inline-flex;
		align-items: center;
		color: var(--ink-4);
		text-decoration: none;
		vertical-align: middle;
		transition: color 0.15s;
	}
	.synthesis-help:hover {
		color: var(--teal-2);
	}
</style>
