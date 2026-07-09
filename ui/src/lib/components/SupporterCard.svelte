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
	<div
		class="grid grid-cols-1 items-center gap-5 rounded-2xl border border-rule-2 bg-paper p-7 text-center sm:grid-cols-[auto_1fr] sm:gap-8 sm:text-left"
	>
		<svg viewBox="0 0 132 132" class="mx-auto size-30">
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
			<text
				x="66"
				y="62"
				text-anchor="middle"
				font-size="30"
				font-family="var(--serif)"
				fill="var(--ink)"
				letter-spacing="-0.02em">{sup.daysLeft}</text
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
		<div
			class="grid w-full grid-cols-1 gap-3 border-t border-rule pt-4 sm:w-auto sm:grid-cols-3 sm:gap-0 sm:border-t-0 sm:border-l sm:pt-0"
		>
			<div class="min-w-0 px-5 sm:border-l sm:border-rule sm:first:border-l-0">
				<div class="font-mono text-[10.5px] tracking-[0.08em] text-ink-4 uppercase">
					Supported with
				</div>
				<div class="mt-1.5 mb-[3px] font-serif text-[21px] text-ink">
					${(sup.totalCents / 100).toLocaleString()}
				</div>
				<div class="font-mono text-[11px] text-ink-3">
					{sup.grantCount}
					{sup.grantCount === 1 ? 'contribution' : 'contributions'}
				</div>
			</div>
			<div class="min-w-0 px-5 sm:border-l sm:border-rule sm:first:border-l-0">
				<div class="font-mono text-[10.5px] tracking-[0.08em] text-ink-4 uppercase">
					Active through
				</div>
				<div class="mt-1.5 mb-[3px] font-serif text-[21px] text-ink">{fmtDate(sup.expiresAt)}</div>
				<div class="font-mono text-[11px] text-ink-3">then reverts to free</div>
			</div>
			<div class="min-w-0 px-5 sm:border-l sm:border-rule sm:first:border-l-0">
				<div class="font-mono text-[10.5px] tracking-[0.08em] text-ink-4 uppercase">
					Supporter since
				</div>
				<div class="mt-1.5 mb-[3px] font-serif text-[21px] text-ink">{fmtDate(sup.since)}</div>
				<div class="font-mono text-[11px] text-ink-3">no subscription</div>
			</div>
		</div>
	</div>
{:else if showCta}
	<div
		class="grid grid-cols-1 items-start justify-items-center gap-5 rounded-2xl border border-teal-2 bg-paper p-7 text-center shadow-[0_0_0_1px_var(--teal-2)] sm:justify-items-start sm:text-left"
	>
		<div>
			<h2 class="section-heading text-2xl">You're on the free tier.</h2>
			<p class="mt-2 max-w-[48ch] text-sm text-ink-2">
				Every 10-K and 10-Q synthesis is free with your account. Supporters unlock the full 10-K
				history, get early access to new features as they ship, and cover the compute and R&D that
				keep it all running.
			</p>
		</div>
		<a
			href="/support"
			class="inline-flex w-fit items-center gap-[7px] rounded-[10px] border border-teal-2 bg-teal-2 px-[18px] py-2.5 font-mono text-[13px] font-medium text-white no-underline transition-all hover:brightness-[1.06]"
			>Become a supporter</a
		>
	</div>
{/if}
