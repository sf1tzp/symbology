<script lang="ts">
	import { enhance } from '$app/forms';
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import SupporterBadges from '$lib/components/SupporterBadges.svelte';
	import ChangeCard from '$lib/components/ChangeCard.svelte';
	import ChangeKindTag from '$lib/components/ChangeKindTag.svelte';
	import { changeKindColor } from '$lib/utils/changes';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import FileText from '@lucide/svelte/icons/file-text';
	import Plus from '@lucide/svelte/icons/plus';
	import Settings from '@lucide/svelte/icons/settings';
	import X from '@lucide/svelte/icons/x';

	let { data } = $props();

	const watchedIds = $derived(new Set(data.watching.map((c) => c.company_id)));
	const feed = $derived(data.feed);
	const calendar = $derived(data.calendar ?? []);
	const calendarMissing = $derived(data.calendarMissing ?? []);

	/** "Feb 25" from an ISO date-only string (parsed as UTC to avoid TZ shift). */
	function fmtDay(iso: string): string {
		return new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	}
	const pctColor = (p: number) =>
		p > 0 ? 'var(--teal-2)' : p < 0 ? 'var(--danger)' : 'var(--ink-3)';

	// ── Time-of-day greeting ──
	// A handful of greetings per slot, picked at random. Computed in onMount so it
	// uses the visitor's local clock (not the server's UTC) and the random pick
	// doesn't trip a hydration mismatch; "Welcome back" is the SSR fallback.
	const GREETINGS: Record<string, string[]> = {
		morning: ['Good morning', 'Morning', 'Bright and early'],
		afternoon: ["'Afternoon", 'Back at it', 'Salutations'],
		evening: ['Good evening'],
		night: ['Still up', 'Working late']
	};
	function greetingSlot(hour: number): keyof typeof GREETINGS {
		if (hour < 5) return 'night';
		if (hour < 12) return 'morning';
		if (hour < 17) return 'afternoon';
		if (hour < 21) return 'evening';
		return 'night';
	}
	let greeting = $state('Welcome back');
	onMount(() => {
		const options = GREETINGS[greetingSlot(new Date().getHours())];
		greeting = options[Math.floor(Math.random() * options.length)];
	});

	// ── Add-company search ──
	type SearchResult = { id: string; ticker: string; name: string; display_name: string | null };
	let adding = $state(false);
	let query = $state('');
	let results = $state<SearchResult[]>([]);
	let searching = $state(false);
	let searchToken = 0;

	async function runSearch() {
		const q = query.trim();
		if (q.length < 1) {
			results = [];
			return;
		}
		const token = ++searchToken;
		searching = true;
		try {
			const res = await fetch(`/api/companies?search=${encodeURIComponent(q)}&limit=8`);
			const body = res.ok ? await res.json() : { companies: [] };
			if (token === searchToken) results = body.companies ?? [];
		} finally {
			if (token === searchToken) searching = false;
		}
	}

	let debounce: ReturnType<typeof setTimeout> | undefined;
	function onInput() {
		clearTimeout(debounce);
		debounce = setTimeout(runSearch, 200);
	}

	function closeAdd() {
		adding = false;
		query = '';
		results = [];
	}
</script>

<svelte:head><title>Watchlist · Symbology</title></svelte:head>

<div class="page">
	<!-- Header -->
	<section class="grid items-end gap-12 md:grid-cols-2">
		<div class="min-w-0">
			<div class="flex-between mb-3.5 gap-4">
				<div class="eyebrow">
					● &nbsp;Your watchlist · {data.watching.length}
					{data.watching.length === 1 ? 'company' : 'companies'}
				</div>
				<a
					href={resolve('/a/settings')}
					class="meta inline-flex items-center gap-1 whitespace-nowrap text-ink-4 no-underline transition-colors hover:text-ink"
				>
					<Settings class="h-3.5 w-3.5" /> Account settings
				</a>
			</div>
			<h1 class="display mb-5">
				{greeting},<br /><em>{data.firstName}.</em>
			</h1>
			<p class="lede text-ink-2">
				{#if data.watching.length === 0}
					Your watchlist is empty. Add a company to start tracking its filings and synthesis.
				{:else}
					Here's what you're tracking — recent filings, material changes, and the filings expected
					next.
				{/if}
			</p>
			{#if data.badges.length > 0}
				<div class="mt-6">
					<div class="sub mb-2.5 text-ink-3">Your badges</div>
					<SupporterBadges badges={data.badges} />
				</div>
			{/if}
		</div>
		<div class="grid grid-cols-3 gap-4">
			<div class="stat">
				<div class="stat-label">Watching</div>
				<div class="stat-value">{data.watching.length}</div>
				<div class="meta text-ink-4">Active</div>
			</div>
			<div class="stat">
				<div class="stat-label">New filings</div>
				<div class="stat-value">{feed.stats.newFilings}</div>
				<div class="meta text-ink-4">Last {feed.stats.sinceDays} days</div>
			</div>
			<div class="stat">
				<div class="stat-label">Material changes</div>
				<div class="stat-value">{feed.stats.materialChanges}</div>
				<div class="meta text-ink-4">Across your list</div>
			</div>
		</div>
	</section>

	<!-- Feed + Watching -->
	<section class="hairline-section">
		<div class="grid items-start gap-12 md:grid-cols-2">
			<!-- What changed: merged feed of new filings + material text changes -->
			<div class="min-w-0">
				<h3 class="sub mb-5 text-ink-3">What changed</h3>
				{#if feed.items.length === 0}
					<div class="rounded-lg border border-dashed border-rule p-8 text-center">
						<p class="text-sm text-ink-3">
							{#if data.watching.length === 0}
								Add companies to see new filings and material changes here.
							{:else}
								Nothing new in the last {feed.stats.sinceDays} days. We'll surface filings and material
								changes as they land.
							{/if}
						</p>
					</div>
				{:else}
					<div class="flex flex-col gap-3">
						{#each feed.items as item (item.kind + item.id)}
							{#if item.kind === 'change'}
								<ChangeCard
									href={item.href}
									accent={changeKindColor(item.changeKind ?? '')}
									dot={false}
									summary={item.summary}
								>
									{#snippet header()}
										<div class="flex w-full items-center justify-between gap-3">
											<span class="min-w-0 text-sm text-ink">
												In <span class="font-medium">{item.ticker}</span>'s recent {item.form}
											</span>
											<ChangeKindTag changeKind={item.changeKind ?? ''} />
										</div>
									{/snippet}
									{#snippet footerLeft()}
										<span class="meta text-ink-4">{fmtDay(item.occurredAt)}</span>
									{/snippet}
								</ChangeCard>
							{:else}
								<a
									href={item.href}
									class="flex items-center gap-3 rounded-lg border border-rule p-3 no-underline hover:bg-paper-2"
								>
									<FileText class="h-4 w-4 shrink-0 text-ink-3" />
									<span class="tag tag-solid">{item.ticker}</span>
									<span class="min-w-0 flex-1 truncate text-sm text-ink">
										{item.companyName} filed a {item.form}
									</span>
									<span class="meta whitespace-nowrap text-ink-4">{fmtDay(item.occurredAt)}</span>
								</a>
							{/if}
						{/each}
					</div>
				{/if}
			</div>

			<!-- Watching list -->
			<div class="min-w-0">
				<div class="flex-between mb-5">
					<h3 class="sub text-ink-3">Watching</h3>
					{#if adding}
						<Button variant="ghost" size="sm" onclick={closeAdd}>
							<X class="h-3.5 w-3.5" /> Close
						</Button>
					{:else}
						<Button variant="ghost" size="sm" onclick={() => (adding = true)}>
							<Plus class="h-3.5 w-3.5" /> Add company
						</Button>
					{/if}
				</div>

				{#if adding}
					<div class="mb-4">
						<Input
							bind:value={query}
							oninput={onInput}
							placeholder="Search companies by ticker or name…"
							autofocus
						/>
						{#if query.trim().length > 0}
							<div class="mt-2 overflow-hidden rounded-lg border border-rule">
								{#if searching && results.length === 0}
									<p class="px-3 py-2 text-sm text-ink-4">Searching…</p>
								{:else if results.length === 0}
									<p class="px-3 py-2 text-sm text-ink-4">No matches.</p>
								{:else}
									{#each results as r (r.id)}
										<form
											method="POST"
											action="?/add"
											use:enhance={() => {
												return async ({ update }) => {
													await update();
													closeAdd();
												};
											}}
										>
											<input type="hidden" name="companyId" value={r.id} />
											<button
												type="submit"
												disabled={watchedIds.has(r.id)}
												class="flex w-full items-center gap-3 border-b border-rule px-3 py-2 text-left last:border-b-0 hover:bg-paper-2 disabled:opacity-40"
											>
												<span class="tag tag-solid">{r.ticker}</span>
												<span class="flex-1 truncate text-sm text-ink"
													>{r.display_name ?? r.name}</span
												>
												{#if watchedIds.has(r.id)}
													<span class="meta text-ink-4">Watching</span>
												{:else}
													<Plus class="h-3.5 w-3.5 text-ink-3" />
												{/if}
											</button>
										</form>
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				{/if}

				{#if data.watching.length === 0}
					<p class="py-6 text-sm text-ink-3">Nothing here yet.</p>
				{:else}
					<div>
						{#each data.watching as c (c.company_id)}
							<div class="flex items-center gap-3 border-b border-rule py-4 last:border-b-0">
								<a href={resolve(`/c/${c.ticker}`)} class="contents">
									<span class="tag tag-solid">{c.ticker}</span>
									<div class="min-w-0 flex-1">
										<div class="truncate font-serif text-base text-ink">
											{c.display_name ?? c.name}
										</div>
										<div class="meta mt-0.5 truncate text-ink-3">
											{#if c.nextFiling}
												{c.nextFiling.periodLabel} · est. {fmtDay(c.nextFiling.predictedFilingDate)}
											{:else if c.sic_description}
												{c.sic_description}
											{/if}
											{#if c.changeCount > 0}
												<span class="text-ink-4">
													· {c.changeCount} recent {c.changeCount === 1 ? 'change' : 'changes'}
												</span>
											{/if}
										</div>
									</div>
									{#if c.yoy && c.yoy.percent != null}
										<span
											class="font-mono text-sm whitespace-nowrap"
											style="color: {pctColor(c.yoy.percent)};"
											title="{c.yoy.label} YoY"
										>
											{c.yoy.percent > 0 ? '+' : ''}{c.yoy.percent.toFixed(1)}%
										</span>
									{/if}
								</a>
								<form
									method="POST"
									action="?/remove"
									use:enhance={() => {
										return async ({ update }) => update();
									}}
								>
									<input type="hidden" name="companyId" value={c.company_id} />
									<Button type="submit" variant="ghost" size="sm" title="Remove from watchlist">
										<X class="h-3.5 w-3.5" />
									</Button>
								</form>
								<a href={resolve(`/c/${c.ticker}`)} class="text-ink-4 hover:text-ink">
									<ChevronRight class="h-4 w-4" />
								</a>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</section>

	<!-- Upcoming filings: next estimated filing date for every watched company -->
	<section class="hairline-section">
		<div class="eyebrow mb-2.5">● &nbsp;Upcoming filings · estimated</div>
		<h2 class="section-heading mb-6">On the calendar.</h2>
		{#if calendar.length === 0 && calendarMissing.length === 0}
			<div class="rounded-lg border border-dashed border-rule p-8 text-center">
				<p class="text-sm text-ink-3">
					Add companies to see their next estimated filing dates, projected from each company's
					historical filing cadence.
				</p>
			</div>
		{:else}
			<div>
				{#each calendar as u (u.companyId)}
					<a
						href={resolve(`/c/${u.ticker}`)}
						class="flex items-center gap-4 border-b border-rule py-3.5 no-underline last:border-b-0 hover:bg-paper-2"
					>
						<div class="w-16 shrink-0">
							<div class="font-mono text-sm text-ink">{fmtDay(u.predictedFilingDate)}</div>
							{#if u.overdue}
								<div class="meta text-danger">overdue</div>
							{:else}
								<div class="meta text-ink-4">~{u.daysUntil}d</div>
							{/if}
						</div>
						<span class="tag tag-solid">{u.ticker}</span>
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm text-ink">{u.companyName}</div>
							<div class="meta text-ink-3">{u.periodLabel} · {u.form}</div>
						</div>
						{#if u.confidence === 'low'}
							<span class="meta whitespace-nowrap text-ink-4" title="Low-confidence estimate">
								estimate
							</span>
						{/if}
					</a>
				{/each}
				{#each calendarMissing as m (m.companyId)}
					<a
						href={resolve(`/c/${m.ticker}`)}
						class="flex items-center gap-4 border-b border-rule py-3.5 no-underline last:border-b-0 hover:bg-paper-2"
					>
						<div class="w-16 shrink-0">
							<div class="meta text-ink-4">—</div>
						</div>
						<span class="tag tag-solid">{m.ticker}</span>
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm text-ink">{m.companyName}</div>
							<div class="meta text-ink-4">No estimate yet</div>
						</div>
					</a>
				{/each}
			</div>
			<p class="meta mt-4 text-ink-4">
				Dates are estimated from each company's historical filing cadence, not official SEC
				schedules.
			</p>
		{/if}
	</section>
</div>
