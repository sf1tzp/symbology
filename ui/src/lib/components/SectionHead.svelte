<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		eyebrow?: string;
		heading: string;
		aside?: Snippet;
		class?: string;
	}
	let { eyebrow, heading, aside, class: className = '' }: Props = $props();
</script>

<header
	class="flex-between {className}"
	style="align-items: flex-end; gap: 24px; margin-bottom: 28px;"
>
	<div>
		{#if eyebrow}
			<div class="eyebrow" style="margin-bottom: 10px;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{eyebrow}
			</div>
		{/if}
		<h2 class="section-heading">{heading}</h2>
	</div>
	{#if aside}
		<div>
			{@render aside()}
		</div>
	{/if}
</header>
