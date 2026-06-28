<script lang="ts">
	import type { Component } from 'svelte';

	// A segmented control: a single pill holding mutually-exclusive options, the
	// active one filled. Two modes per option:
	//   • link mode  — give `href`; renders an <a> that navigates (SSR-friendly,
	//                  e.g. the company page's ?form= version switch).
	//   • state mode — omit `href`; renders a <button> that sets `value` (e.g. the
	//                  document page's L1-synthesis / source toggle).
	// `accent` tints the active segment (defaults to teal); `icon` is an optional
	// leading icon component (e.g. a lucide icon).
	export interface SegmentedOption {
		value: string;
		label: string;
		href?: string;
		accent?: string;
		icon?: Component;
	}

	let {
		options,
		value = $bindable(),
		ariaLabel = 'Toggle',
		onselect
	}: {
		options: SegmentedOption[];
		value?: string;
		ariaLabel?: string;
		onselect?: (value: string) => void;
	} = $props();

	const accentOf = (o: SegmentedOption) => o.accent ?? 'var(--teal-2)';
</script>

<div class="seg" role="group" aria-label={ariaLabel}>
	{#each options as o (o.value)}
		{@const active = value === o.value}
		{@const Icon = o.icon}
		{#if o.href}
			<a
				href={o.href}
				class="seg-opt"
				class:active
				style={active ? `--seg-accent: ${accentOf(o)};` : ''}
				aria-current={active ? 'page' : undefined}
			>
				{#if Icon}<Icon class="seg-ico" />{/if}{o.label}
			</a>
		{:else}
			<button
				type="button"
				class="seg-opt"
				class:active
				style={active ? `--seg-accent: ${accentOf(o)};` : ''}
				aria-pressed={active}
				onclick={() => {
					value = o.value;
					onselect?.(o.value);
				}}
			>
				{#if Icon}<Icon class="seg-ico" />{/if}{o.label}
			</button>
		{/if}
	{/each}
</div>

<style>
	.seg {
		display: inline-flex;
		gap: 2px;
		padding: 2px;
		background: var(--paper-2);
		border: 1px solid var(--rule);
		border-radius: 8px;
	}
	.seg-opt {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 3px 10px;
		border: none;
		border-radius: 6px;
		background: transparent;
		font-family: var(--mono);
		font-size: 11px;
		letter-spacing: 0.02em;
		color: var(--ink-3);
		text-decoration: none;
		cursor: pointer;
		white-space: nowrap;
		transition:
			background 0.12s,
			color 0.12s;
	}
	.seg-opt:hover {
		color: var(--ink);
	}
	.seg-opt.active {
		background: var(--paper);
		color: var(--seg-accent, var(--ink));
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}
	/* Icon is a child component, so its class must be reached via :global. */
	.seg-opt :global(.seg-ico) {
		width: 0.85rem;
		height: 0.85rem;
	}
</style>
