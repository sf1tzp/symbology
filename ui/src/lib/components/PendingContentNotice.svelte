<script lang="ts">
	import { ScrollText, ArrowUp } from '@lucide/svelte';

	let {
		// What's pending, e.g. "brief", "filing synthesis", "change report".
		label = 'analysis',
		// Optional subject for a more specific line, e.g. a company name.
		subject = null
	}: { label?: string; subject?: string | null } = $props();
</script>

<div class="pending-notice">
	<ScrollText class="mx-auto mb-3 h-6 w-6" style="color: var(--ink-4);" />
	<p class="body-text" style="color: var(--ink-3);">
		{#if subject}
			The {label} for {subject} is waiting to be generated.
		{:else}
			This {label} is waiting to be generated.
		{/if}
	</p>
	<button type="button" class="bump-btn" disabled title="Coming soon">
		<ArrowUp class="h-3.5 w-3.5" />
		Bump priority
	</button>
</div>

<style>
	.pending-notice {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: 4rem 0;
	}
	/* Mirrors the disabled .activation-btn pattern from the company masthead. */
	.bump-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		margin-top: 1.25rem;
		padding: 0.5rem 0.875rem;
		font-size: 13px;
		font-family: var(--sans);
		font-weight: 500;
		color: var(--ink-2);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 8px;
		cursor: not-allowed;
		opacity: 0.55;
	}
</style>
