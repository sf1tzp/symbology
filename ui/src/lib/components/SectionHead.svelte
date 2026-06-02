<script lang="ts">
	import type { Snippet } from 'svelte';
	import SynthesisHelp from './SynthesisHelp.svelte';

	interface Props {
		eyebrow?: string;
		heading: string;
		aside?: Snippet;
		/** Show a (?) glyph after the eyebrow linking to the synthesis-levels FAQ. */
		synthesisHelp?: boolean;
		class?: string;
	}
	let { eyebrow, heading, aside, synthesisHelp = false, class: className = '' }: Props = $props();
</script>

<header
	class="flex-between {className}"
	style="align-items: flex-end; gap: 24px; margin-bottom: 28px;"
>
	<div>
		{#if eyebrow}
			<div class="eyebrow flex" style="margin-bottom: 10px; align-items: center;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{eyebrow}&nbsp;
				{#if synthesisHelp}<SynthesisHelp />{/if}
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
