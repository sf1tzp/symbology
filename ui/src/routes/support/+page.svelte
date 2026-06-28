<script lang="ts">
	import { page } from '$app/state';
	import Heart from '@lucide/svelte/icons/heart';
	import Check from '@lucide/svelte/icons/check';
	import PenLine from '@lucide/svelte/icons/pen-line';
	import SupporterCard from '$lib/components/SupporterCard.svelte';
	import {
		amountBadges,
		badgeMilestones,
		daysAllowedBeforeCap,
		MAXXING_BADGE,
		BADGE_HEX,
		MIN_DAYS,
		DEFAULT_DAYS,
		ONE_TIME_DAYS,
		ONE_TIME_PRICE,
		DAY_MS
	} from '$lib/supporter-plans';

	// `form` carries a failed-checkout message; `?canceled=1` comes back when a
	// user abandons Stripe Checkout. `data.supporter` lets us tailor the page for
	// existing supporters (their standing, and how much room is left under the cap).
	let { data, form } = $props();
	let canceled = $derived(page.url.searchParams.get('canceled') === '1');

	// `now` is read once at module init so SSR and the first client render agree
	// (avoids a hydration mismatch from Date.now() drifting between the two).
	const now = Date.now();

	// ── Duration plan: $1 a day. The slider runs the full range up to the policy
	// cap (Dec 31 2028), stacked onto any window the user already holds.
	// Intentional one-time snapshot: this seeds the mutable `days` slider below, so
	// it must NOT reactively reset when `data` changes out from under the user.
	// svelte-ignore state_referenced_locally
	const capRemaining = daysAllowedBeforeCap(data.supporter?.expiresAt ?? null, now);
	const effectiveMax = capRemaining; // the cap is the only ceiling
	const durationAtCap = capRemaining < MIN_DAYS; // no room for the smallest pledge
	const oneTimeAllowed = capRemaining >= ONE_TIME_DAYS;

	let days = $state(Math.min(DEFAULT_DAYS, Math.max(MIN_DAYS, effectiveMax)));

	const fmtDate = (d: Date) =>
		d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

	let thru = $derived(fmtDate(new Date(now + days * DAY_MS)));
	let fillPct = $derived(
		effectiveMax > MIN_DAYS ? ((days - MIN_DAYS) / (effectiveMax - MIN_DAYS)) * 100 : 0
	);
	// The fun easter-egg badges for the currently-selected amount (they stack —
	// e.g. 256 earns both "Integer Overflow" and "Power of 2"). Picking the very
	// top of the slider tops the window out to the cap, which earns the gold
	// "Window Maxxing" badge on top. May be empty.
	let badges = $derived([...amountBadges(days), ...(days === effectiveMax ? [MAXXING_BADGE] : [])]);

	// ── Slider snapping. There are hundreds of selectable values, so landing on a
	// special "badge" number by drag alone is fiddly. We give those milestones a
	// magnetic pull: while dragging, a value within `snapRadius` of one snaps to
	// it. Radius scales with the range (~1%) so the capture zone feels consistent
	// regardless of how far off the cap is. Typing an exact value (below) bypasses
	// this entirely.
	const milestones = $derived(badgeMilestones(MIN_DAYS, effectiveMax));
	const snapRadius = $derived(Math.max(3, Math.round((effectiveMax - MIN_DAYS) / 100)));
	// Only the magnet should fight a drag — keyboard arrows must still nudge by 1,
	// so snapping is gated on an active pointer drag.
	let dragging = $state(false);
	function snapDays(v: number): number {
		let best = v;
		let bestDist = snapRadius + 1;
		for (const m of milestones) {
			const dist = Math.abs(m - v);
			if (dist <= snapRadius && dist < bestDist) {
				best = m;
				bestDist = dist;
			}
		}
		return Math.min(effectiveMax, Math.max(MIN_DAYS, best));
	}

	// ── Exact entry. The big "$N" display is clickable: it swaps to a number input
	// so a supporter can type a precise value (clamped to range) instead of hunting
	// for it on the slider. Typed values are taken as-is — no snapping.
	let editing = $state(false);
	let draft = $state('');
	function startEdit() {
		draft = String(days);
		editing = true;
	}
	function commitEdit() {
		const n = Math.round(Number(draft));
		if (draft.trim() !== '' && Number.isFinite(n)) {
			days = Math.min(effectiveMax, Math.max(MIN_DAYS, n));
		}
		editing = false;
	}
	function focusSelect(node: HTMLInputElement) {
		node.focus();
		node.select();
	}

	// ── Tier feature lists ──
	const freeFeatures: string[] = [
		'Multi-level synthesis: an overview of business activity through the post-pandemic era',
		'See the evolution of risk factors and business strategy, year over year',
		'View selected diffs between source filings',
		'Build watchlists and get notified when fresh 10-K synthesis is ready',
		'Follow the whole synthesis chain: source filing → L1 → L2 → L3'
	];
	const supporterFeatures: string[] = [
		'Quarterly synthesis — an up-to-date view of the current fiscal year',
		'Every source diff, plus advanced embeddings features as they ship (advanced search, cross-company & cross-industry comparative synthesis)',
		'Request synthesis for a new company, or jump one to the front of the queue'
	];

	const faqs: [string, string][] = [
		[
			'Is this a subscription?',
			"No. Both options are one-time payments: $20 for 14 days, or $1/day for any stretch from 33 days up to our current Dec 31, 2028 cap. Nothing auto-renews and there's nothing to cancel."
		],
		[
			'What happens when it lapses?',
			'Your account simply returns to the free tier. Nothing is deleted, and you’re never locked out of raw filings or 10-K synthesis.'
		],
		[
			'Can I add more days later?',
			'Yes — top up the $1/day option anytime and the days stack onto whatever you have left. Supporter windows are currently capped at Dec 31, 2028; we may introduce new tiers as the project matures.'
		]
	];
</script>

<svelte:head>
	<title>Support Symbology</title>
	<meta
		name="description"
		content="Symbology is independent and sourced straight from EDGAR. We're early — supporters help cover the synthesis compute and unlock everything as a thank-you."
	/>
</svelte:head>

<div class="mx-auto max-w-[1100px]">
	<!-- ── Hero ── -->
	<section class="pt-8 text-center">
		<div class="eyebrow mb-[1.4rem] flex justify-center">
			<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;EARLY-SUPPORTER SPECIAL
		</div>
		<h1 class="display mx-auto mt-0 mb-6 max-w-[16ch]">
			Keep the synthesis <em>running.</em>
		</h1>
		<p class="lede mx-auto my-0 max-w-[60ch] text-ink-2">
			As we catch up on existing filings, we're seeking early adopters to pitch in!
		</p>
		<p class="lede mx-auto my-2 max-w-[60ch] text-ink-2">
			Show your support - for just $1/day secure your access to advanced features and support
			ongoing symbology operations.
		</p>
		<span class="tag mt-4 border-transparent bg-sage-2 px-[14px] py-[6px] text-teal-2">
			Now through Dec 31, 2026, receive an Early-Supporter badge for your profile
		</span>
	</section>

	<!-- Active supporters see their standing here; non-supporters get the plans
	     below without a redundant upsell card (showCta={false}). -->
	{#if data.supporter?.active}
		<section class="mt-12">
			<SupporterCard supporter={data.supporter} showCta={false} />
			<p class="meta mt-4 text-center text-ink-4">
				Thanks for keeping it running — topping up below stacks onto your current window.
			</p>
		</section>
	{/if}

	<!-- ── Plans ── -->
	<section class="mt-14">
		{#if form?.message}
			<p
				class="mb-6 rounded-lg border border-l-[3px] border-rule border-l-danger bg-paper-2 px-4 py-3 text-center text-sm text-danger"
			>
				{form.message}
			</p>
		{:else if canceled}
			<p
				class="mb-6 rounded-lg border border-l-[3px] border-rule border-l-teal-2 bg-paper-2 px-4 py-3 text-center text-sm text-ink-2"
			>
				Checkout canceled — no charge was made. Support whenever you're ready.
			</p>
		{/if}
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
			<!-- One-time support -->
			<div class="relative flex flex-col rounded-2xl border border-rule-2 bg-paper p-8">
				<div class="font-mono text-[11px] tracking-[0.1em] text-ink-3 uppercase">
					One-time support
				</div>
				<div
					class="mt-4 mb-1 font-serif text-[52px] leading-none tracking-[-0.03em] text-ink md:text-[60px]"
				>
					${ONE_TIME_PRICE} <span class="text-[32px]">Lunch Special</span>
				</div>
				<div class="mb-[14px] font-serif text-[19px] text-teal-2">
					{ONE_TIME_DAYS} days of supporter status
				</div>
				<div class="mb-6 text-[14.5px] leading-[1.6] text-ink-2">
					<p>
						Show your support and buy us some lunch. ${ONE_TIME_PRICE} gets you {ONE_TIME_DAYS} days access
						to Symbology.
					</p>
					<p class="mt-2">Catch up on the latest filings. Then, Like what you see?</p>
					<p class="mt-2">Come back and lock in for $1/day.</p>
				</div>
				<form method="POST" action="?/checkout" class="mt-auto">
					<input type="hidden" name="plan" value="one" />
					<button
						type="submit"
						class="inline-flex w-full cursor-pointer items-center justify-center gap-[7px] rounded-[10px] border border-ink bg-ink px-4 py-[13px] font-mono text-[14.5px] font-medium tracking-[0.01em] text-paper no-underline transition-all duration-[120ms] hover:border-rule-2 hover:bg-[color-mix(in_oklab,var(--ink)_88%,#000)] disabled:cursor-not-allowed disabled:opacity-[0.45]"
						disabled={!oneTimeAllowed}
					>
						Support once · ${ONE_TIME_PRICE}
					</button>
				</form>
				<div class="mt-4 font-mono text-[11.5px] text-ink-4">
					{#if oneTimeAllowed}
						One-time payment · expires after {ONE_TIME_DAYS} days
					{:else}
						Your window already reaches the Dec 31, 2028 cap
					{/if}
				</div>
			</div>

			<!-- Pick-your-duration -->
			<div
				class="relative flex flex-col rounded-2xl border border-teal-2 bg-paper p-8 shadow-[0_0_0_1px_var(--teal-2)]"
			>
				{#if durationAtCap}
					<span
						class="absolute -top-[11px] left-8 rounded-full bg-teal-2 px-3 py-1 font-mono text-[10px] tracking-[0.1em] text-white uppercase"
						>You're all set</span
					>
					<div class="font-mono text-[11px] tracking-[0.1em] text-ink-3 uppercase">
						Pay what you want · $1 a day
					</div>
					<div
						class="mt-4 mb-1 font-serif text-[52px] leading-none tracking-[-0.03em] text-ink md:text-[60px]"
					>
						—
					</div>
					<div class="mb-[14px] font-serif text-[19px] text-teal-2">Supported through the cap</div>
					<div class="mb-6 text-[14.5px] leading-[1.6] text-ink-2">
						Your supporter window already reaches our current cap of <b>Dec 31, 2028</b>. Thank you
						— there's nothing more to add right now. We may open up longer windows as the project
						matures.
					</div>
				{:else}
					<div class="flex"></div>
					<span
						class="absolute -top-[11px] left-8 rounded-full bg-teal-2 px-3 py-1 font-mono text-[10px] tracking-[0.1em] text-white uppercase"
						>Pick your duration</span
					>
					<div class="font-mono text-[11px] tracking-[0.1em] text-ink-3 uppercase">
						Pay what you want · $1 a day
					</div>
					<div
						class="mt-4 mb-1 font-serif text-[52px] leading-none tracking-[-0.03em] text-ink md:text-[60px]"
					>
						{#if editing}
							<span class="align-baseline">$</span><input
								type="text"
								inputmode="numeric"
								bind:value={draft}
								use:focusSelect
								onblur={commitEdit}
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										commitEdit();
									} else if (e.key === 'Escape') {
										editing = false;
									}
								}}
								aria-label="Number of days to support"
								class="w-[3.6ch] border-b-2 border-teal-2 bg-transparent font-serif text-[52px] leading-none tracking-[-0.03em] text-ink outline-none md:text-[60px]"
							/>
						{:else}
							<button
								type="button"
								onclick={startEdit}
								title="Click to type an exact number of days"
								class="cursor-text bg-transparent p-0 font-serif text-[52px] leading-none tracking-[-0.03em] text-ink underline decoration-rule-2 decoration-dotted decoration-1 underline-offset-8 md:text-[60px]"
								>${days}</button
							>
						{/if}<small class="ml-1.5 font-sans text-[17px] font-normal tracking-normal text-ink-3"
							><PenLine class="mr-1 inline size-3 align-middle text-ink" aria-hidden="true" />{days} days</small
						>
					</div>
					<div class="mb-4 font-serif text-[19px] text-teal-2">
						{days} days of supporter status
					</div>

					<!-- Badges stack, so this row holds a variable number of pills. It's a
					     fixed-height (min-h-9), non-wrapping, clipped row so the count can
					     change as the slider moves without shifting the content below; an
					     invisible spacer holds the height when nothing qualifies. -->
					<div class="mb-4 flex min-h-9 flex-nowrap items-center gap-2 overflow-hidden font-mono">
						{#each badges as b (b.key)}
							<span
								class="inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1"
								style="color: {BADGE_HEX[b.color]}; border-color: color-mix(in oklab, {BADGE_HEX[
									b.color
								]} 45%, transparent); background: color-mix(in oklab, {BADGE_HEX[
									b.color
								]} 12%, transparent);"
							>
								<span class="text-sm leading-none">{b.emoji}</span>
								<span class="text-xs whitespace-nowrap">{b.label}</span>
							</span>
						{/each}
						{#if badges.length === 0}
							<span class="invisible text-xs leading-none">Hi</span>
						{/if}
					</div>

					<div class="mb-6">
						<div class="mb-4 flex items-baseline justify-between">
							<span class="font-serif text-[22px] tracking-[-0.01em] text-ink"
								>Support for <b class="font-normal text-teal-2">{days} days</b></span
							>
							<span class="font-mono text-[11px] text-ink-4">unlocks through {thru}</span>
						</div>

						<input
							class="dur-range h-1 w-full cursor-pointer rounded-full outline-none"
							type="range"
							min={MIN_DAYS}
							max={effectiveMax}
							step={1}
							value={days}
							onpointerdown={() => (dragging = true)}
							onpointerup={() => (dragging = false)}
							onpointercancel={() => (dragging = false)}
							oninput={(e) => {
								const raw = e.currentTarget.valueAsNumber;
								days = dragging ? snapDays(raw) : raw;
							}}
							aria-label="Number of days to support"
							style="background: linear-gradient(to right, var(--teal-2) {fillPct}%, var(--rule-2) {fillPct}%);"
						/>
						<div class="mt-2.5 flex justify-between font-mono text-[10.5px] text-ink-4">
							<span>{MIN_DAYS} days</span><span>{effectiveMax} days</span>
						</div>
						<p class="mt-3 font-mono text-[11px] text-ink-4">
							Supporter window currently capped Dec 31, 2028
						</p>
					</div>

					<div class="mb-6 text-[14.5px] leading-[1.6] text-ink-2">
						<p>Access new and advanced features for just $1/day - lock in now thru 2029!</p>
						<p class="mt-2">Unlock special profile badges by supporting with specific amounts</p>
					</div>
					<form method="POST" action="?/checkout" class="mt-auto">
						<input type="hidden" name="plan" value="duration" />
						<input type="hidden" name="days" value={days} />
						<button
							type="submit"
							class="inline-flex w-full cursor-pointer items-center justify-center gap-[7px] rounded-[10px] border border-teal-2 bg-teal-2 px-4 py-[13px] font-mono text-[14.5px] font-medium tracking-[0.01em] text-white no-underline transition-all duration-[120ms] hover:border-rule-2 hover:brightness-[1.06]"
						>
							<Heart class="h-3 w-3 fill-current" /> Support {days} days · ${days}
						</button>
					</form>
					<div class="mt-[14px] font-mono text-[11.5px] text-ink-4">
						One-time payment · ${days} for {days} days · top up anytime, days stack
					</div>
				{/if}
			</div>
		</div>
		<p class="meta mt-5 text-center text-ink-4">
			No subscriptions — both are one-time payments · secure checkout · cards &amp; Apple Pay · when
			status lapses your account simply returns to the free tier
		</p>
	</section>

	<!-- ── What you get: free vs supporter ── -->
	<section class="hairline-section">
		<div class="mb-8 text-center">
			<div class="eyebrow mb-[0.6rem] flex justify-center">
				<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;WHAT YOU GET
			</div>
			<h2 class="section-heading">Free, and with supporter status.</h2>
		</div>
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
			<!-- Free tier -->
			<div class="rounded-2xl border border-rule bg-paper p-8">
				<div class="mb-5">
					<div class="mb-2 font-mono text-[11px] tracking-[0.1em] text-ink-3 uppercase">
						Free · everyone
					</div>
					<h3 class="font-serif text-xl leading-[1.25] tracking-[-0.01em] text-ink">
						Look back on 5 years of filings
					</h3>
				</div>
				<ul class="m-0 flex list-none flex-col gap-[14px] p-0">
					{#each freeFeatures as f (f)}
						<li class="flex items-start gap-3 text-[14.5px] leading-[1.5] text-ink-2">
							<span
								class="mt-px inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-rule text-ink-3"
								><Check class="h-[14px] w-[14px]" strokeWidth={2.6} /></span
							>
							<span>{f}</span>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Supporter tier -->
			<div
				class="rounded-2xl border border-teal-2 bg-[color-mix(in_oklab,var(--sage-2)_30%,var(--paper))] p-8 shadow-[0_0_0_1px_var(--teal-2)]"
			>
				<div class="mb-5">
					<div class="mb-2 font-mono text-[11px] tracking-[0.1em] text-ink-3 uppercase">
						Supporter · $20 or $1/day
					</div>
					<h3 class="font-serif text-xl leading-[1.25] tracking-[-0.01em] text-ink">
						Everything in free, plus the current quarter
					</h3>
				</div>
				<ul class="m-0 flex list-none flex-col gap-[14px] p-0">
					{#each supporterFeatures as f (f)}
						<li class="flex items-start gap-3 text-[14.5px] leading-[1.5] text-ink-2">
							<span
								class="mt-px inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-sage-2 text-teal-2"
								><Check class="h-[14px] w-[14px]" strokeWidth={2.6} /></span
							>
							<span>{f}</span>
						</li>
					{/each}
				</ul>
				<div
					class="mt-6 flex items-start gap-2.5 border-t border-t-[color-mix(in_oklab,var(--teal-2)_30%,transparent)] pt-5 text-[13.5px] leading-[1.5] text-ink-2"
				>
					<span class="flex-none text-base leading-[1.3] text-teal-2">✦</span>
					<span>
						Support during this initial push and you'll earn an <b>early-supporter badge</b> on your profile.
						Thank you for backing it early.
					</span>
				</div>
			</div>
		</div>
	</section>

	<!-- ── Support log: honest early-stage placeholder ── -->
	<!-- TODO: Implement -->
	<!-- <section class="hairline-section">
		<div class="flex flex-wrap items-baseline justify-between gap-4">
			<div>
				<div class="eyebrow mb-[0.6rem] flex items-center">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;SUPPORT LOG
				</div>
				<h2 class="section-heading">Be one of the first.</h2>
			</div>
		</div>
		<div
			class="mt-6 rounded-xl border border-dashed border-rule-2 p-8 text-center text-[14.5px] leading-[1.6] text-ink-2"
		>
			<p class="mx-auto my-0 max-w-[56ch]">
				This is where supporters show up. Supporters will be listed here as
				they come in, by first name + last initial (or “Anonymous” if you'd rather stay private).
			</p>
			<p class="mt-3 mb-0 font-mono text-[11.5px] text-ink-4">
				No supporters to show yet. The next name here could be yours.
			</p>
		</div>
	</section> -->

	<!-- ── Why support ── -->
	<section class="hairline-section">
		<div class="two-col">
			<div>
				<div class="eyebrow mb-[0.6rem] flex items-center">
					<span class="text-teal-2">&#9679;</span>&nbsp;&nbsp;WHY SUPPORT
				</div>
				<h3 class="section-heading text-2xl">Where your support goes</h3>
			</div>
			<div class="flex flex-col gap-6">
				<p class="body-text text-[1.0625rem] text-ink-2">
					Symbology is an independent operation that relies heavily on Local LLMs -
					<strong class="text-ink"
						>the vast majority of Symbology's synthesis runs on consumer hardware</strong
					>. That keeps our costs low and avoids reliance on large datacenters as much as possible.
				</p>
				<p class="body-text text-[1.0625rem] text-ink-2">
					We're using this time to refine our content quality and explore advanced synthesis
					possibilities.
				</p>
				<p class="body-text text-[1.0625rem] text-ink-2">
					Your support goes toward <strong class="text-ink">ongoing synthesis</strong>, expanding
					our operational capacity, and additional R&amp;D and feature work.
				</p>
				<div class="flex flex-wrap gap-2.5">
					<span class="tag">No subscriptions</span>
					<span class="tag">Open source</span>
					<span class="tag tag-mono">Independent</span>
					<span class="tag tag-mono">Sourced Direct from SEC EDGAR</span>
				</div>
			</div>
		</div>
	</section>

	<!-- ── FAQ ── -->
	<section class="hairline-section mb-8">
		<div class="grid-3 max-md:gap-6">
			{#each faqs as [q, a] (q)}
				<div>
					<h4 class="mt-0 mb-2.5 font-serif text-[19px] font-normal tracking-[-0.01em] text-ink">
						{q}
					</h4>
					<p class="body-text text-[0.9rem] leading-[1.6] text-ink-2">
						{a}
					</p>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	/* The range-slider thumb is the one piece that can't be expressed as Tailwind
	   utilities — it lives in vendor pseudo-elements. Everything else on this page
	   is utility classes (palette tokens are exposed as color/font utilities in
	   app.css). The track fill is set inline via a runtime linear-gradient. */
	.dur-range {
		-webkit-appearance: none;
		appearance: none;
	}
	.dur-range::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--teal-2);
		border: 3px solid var(--paper);
		box-shadow:
			0 0 0 1px var(--teal-2),
			0 2px 6px rgba(0, 0, 0, 0.18);
		cursor: grab;
		transition: transform 0.1s;
	}
	.dur-range::-webkit-slider-thumb:active {
		cursor: grabbing;
		transform: scale(1.12);
	}
	.dur-range::-moz-range-thumb {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--teal-2);
		border: 3px solid var(--paper);
		box-shadow:
			0 0 0 1px var(--teal-2),
			0 2px 6px rgba(0, 0, 0, 0.18);
		cursor: grab;
	}
</style>
