<script lang="ts">
	import type { Snippet } from 'svelte';
	import SynthesisHelp from './SynthesisHelp.svelte';
	import DiffHelp from './diffHelp.svelte';

	interface Props {
		eyebrow?: string;
		heading: string;
		aside?: Snippet;
		/** Show a (?) glyph after the eyebrow linking to the synthesis-levels FAQ. */
		synthesisHelp?: boolean;
		diffHelp?: boolean;
		/**
		 * Pin the eyebrow to the top of the viewport while the enclosing section
		 * scrolls past. The pinned content lives in a sticky container rendered as
		 * a direct child of the parent (Svelte adds no wrapper element of its own),
		 * so its containing block spans the whole section. Place this SectionHead as
		 * a direct child of the scrolling <section>. The `aside` slot keeps its
		 * inline-row layout only in the non-sticky variant.
		 */
		sticky?: boolean;
		/**
		 * Pin the heading along with the eyebrow (implies `sticky`). Both ride in
		 * the same sticky container, so the heading needs no second top offset — it
		 * sits directly under the eyebrow in the pinned bar.
		 */
		stickyHeading?: boolean;
		class?: string;
	}
	let {
		eyebrow,
		heading,
		aside,
		synthesisHelp = false,
		diffHelp = false,
		sticky = false,
		stickyHeading = false,
		class: className = ''
	}: Props = $props();

	const pinned = $derived(sticky || stickyHeading);

	// While pinned, publish the sticky bar's height to the parent element as the
	// --md-heading-sticky-top CSS variable. Descendants in the same container use
	// it to (a) pin sticky MarkdownContent headings *beneath* this bar instead of
	// overlapping it, and (b) offset deep-link scroll targets (scroll-margin-top)
	// so anchored content lands below the bar rather than under it.
	//
	// Pinning is mobile-only (the bar is static at md+), so the variable is
	// published only while the mobile media query matches — that way it reads as
	// the *current* sticky offset, and desktop deep-links keep their own offset.
	// bind:clientHeight keeps the value correct across viewport/orientation/font
	// changes, and includes the bar's border so content sits below the divider.
	let bar = $state<HTMLElement>();
	let barHeight = $state(0);
	$effect(() => {
		const parent = bar?.parentElement;
		if (!parent) return;
		const mobile = window.matchMedia('(max-width: 767.98px)');
		const sync = () => {
			if (pinned && mobile.matches && barHeight > 0) {
				// -2 closes a slight visible gap between the bar and content below it.
				parent.style.setProperty('--md-heading-sticky-top', `${barHeight - 2}px`);
			} else {
				parent.style.removeProperty('--md-heading-sticky-top');
			}
		};
		sync();
		mobile.addEventListener('change', sync);
		return () => {
			mobile.removeEventListener('change', sync);
			parent.style.removeProperty('--md-heading-sticky-top');
		};
	});
</script>

{#if pinned}
	<!--
		The eyebrow (and, when stickyHeading is set, the heading) ride in one sticky
		container. Because the container is a direct child of the enclosing
		<section>, its containing block is the whole section, so it pins across it.
	-->
	<div
		bind:this={bar}
		bind:clientHeight={barHeight}
		class="eyebrow-sticky {stickyHeading
			? 'eyebrow-sticky--heading'
			: ''} bg-background/80 backdrop-blur-md"
	>
		{#if eyebrow}
			<div
				class="eyebrow flex"
				style="align-items: center; {stickyHeading ? 'margin-bottom: 8px;' : ''}"
			>
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{eyebrow}&nbsp;
				{#if synthesisHelp}<SynthesisHelp />{/if}
				{#if diffHelp}<DiffHelp />{/if}
			</div>
		{/if}
		{#if stickyHeading}
			<h2 class="section-heading">{heading}</h2>
		{/if}
	</div>
	{#if !stickyHeading}
		<h2 class="section-heading" style="margin-top: 10px; margin-bottom: 28px;">{heading}</h2>
	{/if}
	{#if aside}
		<div style="margin-bottom: 28px;">
			{@render aside()}
		</div>
	{/if}
{:else}
	<header
		class="flex-between {className}"
		style="align-items: flex-end; gap: 24px; margin-bottom: 28px;"
	>
		<div>
			{#if eyebrow}
				<div class="eyebrow flex" style="margin-bottom: 10px; align-items: center;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;{eyebrow}&nbsp;
					{#if synthesisHelp}<SynthesisHelp />{/if}
					{#if diffHelp}<DiffHelp />{/if}
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
{/if}
