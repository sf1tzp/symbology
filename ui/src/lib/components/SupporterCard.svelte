<script lang="ts">
	import type { SupporterStatus } from '$lib/server/db/supporter';

	/**
	 * Supporter standing card, shared by the account settings page and the support
	 * page. When the viewer has an active window it renders the days-left ring plus
	 * the contribution facts; otherwise it shows a free-tier upsell pointing at
	 * `/support`. Pass `showCta={false}` on the support page itself, where the
	 * upsell would just point back at the current page — there it quietly renders
	 * nothing for non-supporters.
	 */
	let { supporter, showCta = true }: { supporter: SupporterStatus | null; showCta?: boolean } =
		$props();

	const DAY_MS = 86_400_000;
	const fmtDate = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleDateString('en-US', {
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				})
			: '—';

	const sup = $derived(supporter);
	// Ring fraction = days remaining over the full window the user has bought
	// (first grant through current expiry). Clamped to [0,1].
	const ringPct = $derived.by(() => {
		if (!sup?.active || !sup.expiresAt || !sup.since) return 0;
		const windowDays = Math.max(
			sup.daysLeft,
			Math.round((new Date(sup.expiresAt).getTime() - new Date(sup.since).getTime()) / DAY_MS)
		);
		return windowDays > 0 ? Math.min(1, sup.daysLeft / windowDays) : 0;
	});
	// SVG ring geometry (r=54 → circumference); dashoffset draws the remaining arc.
	const RING_C = 2 * Math.PI * 54;
	const ringOffset = $derived(RING_C * (1 - ringPct));
</script>

{#if sup?.active}
	<div class="sup-card">
		<div class="sup-ring">
			<svg viewBox="0 0 132 132" class="ring">
				<circle cx="66" cy="66" r="54" fill="none" stroke="var(--rule)" stroke-width="9" />
				<circle
					cx="66"
					cy="66"
					r="54"
					fill="none"
					stroke="var(--teal-2)"
					stroke-width="9"
					stroke-linecap="round"
					stroke-dasharray={RING_C}
					stroke-dashoffset={ringOffset}
					transform="rotate(-90 66 66)"
				/>
				<text x="66" y="62" text-anchor="middle" font-size="30" font-family="var(--serif)"
					>{sup.daysLeft}</text
				>
				<text
					x="66"
					y="84"
					text-anchor="middle"
					font-size="11"
					font-family="var(--mono)"
					fill="var(--ink-4)"
					letter-spacing="0.08em">DAYS LEFT</text
				>
			</svg>
		</div>
		<div class="sup-facts">
			<div>
				<div class="sup-k">Supported with</div>
				<div class="sup-v">${(sup.totalCents / 100).toLocaleString()}</div>
				<div class="sup-s">
					{sup.latestPlan === 'one' ? 'one-time · 14 days' : 'one-time · $1 a day'}
				</div>
			</div>
			<div>
				<div class="sup-k">Active through</div>
				<div class="sup-v">{fmtDate(sup.expiresAt)}</div>
				<div class="sup-s">then reverts to free</div>
			</div>
			<div>
				<div class="sup-k">Supporter since</div>
				<div class="sup-v">{fmtDate(sup.since)}</div>
				<div class="sup-s">no subscription</div>
			</div>
		</div>
	</div>
{:else if showCta}
	<div class="sup-card sup-card--cta">
		<div>
			<h2 class="section-heading" style="font-size: 1.5rem;">You're on the free tier.</h2>
			<p class="mt-2 text-sm text-ink-2" style="max-width: 48ch;">
				Raw filings and recent 10-K synthesis are always free. Supporters unlock quarterly
				synthesis, full history, the complete disclosure clusters, and queue prioritization — and
				cover the compute that makes it all run.
			</p>
		</div>
		<a href="/support" class="sup-cta sup-cta--solid">Become a supporter</a>
	</div>
{/if}

<style>
	/* Supporter status card, shared by the settings + support pages. Builds on the
	   global Symbology palette tokens in app.css. */
	.sup-card {
		border: 1px solid var(--rule-2);
		border-radius: 16px;
		padding: 28px;
		background: var(--paper);
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 32px;
		align-items: center;
	}
	.sup-card--cta {
		grid-template-columns: 1fr;
		gap: 20px;
		border-color: var(--teal-2);
		box-shadow: 0 0 0 1px var(--teal-2);
		align-items: start;
	}
	.sup-ring .ring {
		width: 120px;
		height: 120px;
	}
	.sup-ring .ring text {
		fill: var(--ink);
		letter-spacing: -0.02em;
	}
	.sup-facts {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0;
		border-left: 1px solid var(--rule);
	}
	.sup-facts > div {
		padding: 0 20px;
	}
	.sup-facts > div + div {
		border-left: 1px solid var(--rule);
	}
	.sup-k {
		font-family: var(--mono);
		font-size: 10.5px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--ink-4);
	}
	.sup-v {
		font-family: var(--serif);
		font-size: 21px;
		color: var(--ink);
		margin: 6px 0 3px;
	}
	.sup-s {
		font-family: var(--mono);
		font-size: 11px;
		color: var(--ink-3);
	}
	.sup-cta {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		font-family: var(--mono);
		font-size: 13px;
		font-weight: 500;
		padding: 10px 18px;
		border-radius: 10px;
		border: 1px solid var(--rule);
		color: var(--ink);
		text-decoration: none;
		transition: all 0.12s;
	}
	.sup-cta:hover {
		border-color: var(--rule-2);
	}
	.sup-cta--solid {
		background: var(--teal-2);
		border-color: var(--teal-2);
		color: #fff;
		align-self: start;
	}
	.sup-cta--solid:hover {
		filter: brightness(1.06);
	}

	@media (max-width: 640px) {
		.sup-card {
			grid-template-columns: 1fr;
			gap: 20px;
			justify-items: center;
			text-align: center;
		}
		.sup-facts {
			border-left: 0;
			border-top: 1px solid var(--rule);
			padding-top: 16px;
			gap: 12px;
		}
		.sup-facts > div + div {
			border-left: 0;
		}
	}
</style>
