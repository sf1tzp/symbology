<script lang="ts">
	import Heart from '@lucide/svelte/icons/heart';
	import Lock from '@lucide/svelte/icons/lock';

	/**
	 * Editorial locked-content card — the on-brand "this is a supporter perk"
	 * treatment from the design (hatched rule-system card, plain statement of
	 * what's behind it, a Support CTA). Used wherever the server withholds
	 * generated analysis from a free viewer; it never carries the gated content.
	 */
	interface Props {
		title: string;
		note?: string;
		badge?: string;
		cta?: string;
		href?: string;
	}
	let {
		title,
		note,
		badge = 'Supporter',
		cta = 'Become a supporter',
		href = '/support'
	}: Props = $props();
</script>

<div class="locked">
	<span class="lk-badge"><Lock class="h-3 w-3" /> {badge}</span>
	<div class="lk-title">{title}</div>
	{#if note}<div class="lk-note">{note}</div>{/if}
	<a {href} class="lk-cta"><Heart class="h-3 w-3 fill-current" /> {cta}</a>
</div>

<style>
	.locked {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: 16px;
		padding: 48px 40px;
		border: 1px solid var(--rule-2);
		border-radius: 12px;
		background:
			repeating-linear-gradient(
				135deg,
				transparent 0 11px,
				color-mix(in oklab, var(--rule) 55%, transparent) 11px 12px
			),
			var(--paper);
	}
	:global(.dark) .locked {
		background:
			repeating-linear-gradient(
				135deg,
				transparent 0 11px,
				color-mix(in oklab, var(--rule) 70%, transparent) 11px 12px
			),
			var(--paper-2);
	}
	.lk-badge {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		font-family: var(--mono);
		font-size: 10.5px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--teal-2);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 999px;
		padding: 6px 12px;
	}
	.lk-title {
		font-family: var(--serif);
		font-size: 26px;
		color: var(--ink);
		letter-spacing: -0.02em;
		line-height: 1.2;
		max-width: 28ch;
	}
	.lk-note {
		font-size: 14px;
		color: var(--ink-2);
		line-height: 1.55;
		max-width: 52ch;
	}
	.lk-cta {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		margin-top: 6px;
		font-family: var(--mono);
		font-size: 13px;
		font-weight: 500;
		padding: 10px 18px;
		border-radius: 10px;
		background: var(--teal-2);
		border: 1px solid var(--teal-2);
		color: #fff;
		text-decoration: none;
		transition: filter 0.12s;
	}
	.lk-cta:hover {
		filter: brightness(1.06);
	}
</style>
