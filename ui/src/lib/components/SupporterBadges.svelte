<script lang="ts">
	import { BADGE_HEX, type AmountBadge, type BadgeKey } from '$lib/supporter-plans';

	/**
	 * Renders a supporter's earned easter-egg badges. Display-only by default; in
	 * `selectable` mode each badge becomes a button for choosing the profile-icon
	 * avatar, with an "Initials" option to clear the choice. Selection is reported
	 * via `onselect` — the parent owns persistence.
	 */
	let {
		badges,
		selectable = false,
		selectedKey = null,
		initials = '',
		busy = false,
		onselect
	}: {
		badges: AmountBadge[];
		selectable?: boolean;
		selectedKey?: BadgeKey | null;
		initials?: string;
		busy?: boolean;
		onselect?: (key: BadgeKey | null) => void;
	} = $props();
</script>

<div class="badge-row">
	{#each badges as b (b.key)}
		{#if selectable}
			<button
				type="button"
				class="badge selectable"
				class:on={selectedKey === b.key}
				disabled={busy}
				aria-pressed={selectedKey === b.key}
				title="Use {b.label} as your profile icon"
				style="--bc: {BADGE_HEX[b.color]};"
				onclick={() => onselect?.(b.key)}
			>
				<span class="badge-emoji">{b.emoji}</span>
				{b.label}
			</button>
		{:else}
			<span class="badge" style="--bc: {BADGE_HEX[b.color]};">
				<span class="badge-emoji">{b.emoji}</span>
				{b.label}
			</span>
		{/if}
	{/each}

	{#if selectable}
		<button
			type="button"
			class="badge selectable initials-opt"
			class:on={selectedKey === null}
			disabled={busy}
			aria-pressed={selectedKey === null}
			title="Use your initials as your profile icon"
			onclick={() => onselect?.(null)}
		>
			<span class="badge-emoji">{initials || 'Aa'}</span>
			Initials
		</button>
	{/if}
</div>

<style>
	.badge-row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		padding: 6px 13px;
		border-radius: 999px;
		border: 1px solid;
		font-family: var(--mono);
		font-size: 11.5px;
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--bc, var(--teal-2));
		border-color: color-mix(in oklab, var(--bc, var(--teal-2)) 45%, transparent);
		background: color-mix(in oklab, var(--bc, var(--teal-2)) 12%, transparent);
	}
	.badge-emoji {
		font-size: 13px;
		line-height: 1;
	}
	.badge.selectable {
		cursor: pointer;
		transition: all 0.12s;
	}
	.badge.selectable:hover:not(:disabled) {
		filter: brightness(0.97);
	}
	.badge.selectable:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	/* Selected chip: solid ring in the badge colour. */
	.badge.selectable.on {
		box-shadow: 0 0 0 2px color-mix(in oklab, var(--bc, var(--teal-2)) 70%, transparent);
		border-color: var(--bc, var(--teal-2));
	}
	/* The "Initials" option is neutral (no badge colour). */
	.initials-opt {
		--bc: var(--ink-3);
		color: var(--ink-2);
		border-color: var(--rule-2);
		background: var(--paper);
	}
	.initials-opt.on {
		box-shadow: 0 0 0 2px var(--ink-4);
		border-color: var(--ink-3);
	}
</style>
