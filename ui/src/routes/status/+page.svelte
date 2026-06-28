<script lang="ts">
	import { CircleQuestionMark } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import type {
		HeroStats,
		ContentBreakdownRow,
		ModelBreakdownRow,
		ContentLogRow,
		JobQueueStats,
		RecentJobRow,
		WorkerRow
	} from '$lib/server/db/status';
	import StatusDot from '$lib/components/status/StatusDot.svelte';
	import BlinkDot from '$lib/components/status/BlinkDot.svelte';
	import Bar from '$lib/components/status/Bar.svelte';
	import StatusNav from '$lib/components/status/StatusNav.svelte';
	import { STATUS_MESSAGE } from '$lib/status-message';

	let { data }: { data: PageData } = $props();

	// Self-hosting brag — surfaced via the spend tooltip.
	const HOST_SPECS =
		'The majority of content is generated on consumer hardware ' +
		'(Apple M3 Macbook Air 24GB, Nvidia 3060 12GB), which we estimate ~$0.02/hr of compute. ' +
		'Self-hosted generations are metered by compute time at that rate; Claude API calls are counted at Anthropic per-token rates.';

	// Mutable state for polling
	let stat_window = $state<number | null>(data.stat_window);
	let hero = $state<HeroStats | null>(data.hero);
	let contentBreakdown = $state<ContentBreakdownRow[]>(data.contentBreakdown);
	let modelBreakdown = $state<ModelBreakdownRow[]>(data.modelBreakdown);
	let contentLog = $state<ContentLogRow[]>(data.contentLog);
	let queueStats = $state<JobQueueStats | null>(data.queueStats);
	let recentJobs = $state<RecentJobRow[]>(data.recentJobs);
	let workers = $state<WorkerRow[]>(data.workers);

	// ── Recent-jobs status filter ──
	//
	// The scheduler fans out many dependent jobs and parks parents in backoff, so
	// the live tail fills with pending work. A filter lets an operator pull just
	// failed / backoff / completed jobs — and because a filtered fetch is a
	// deliberate server query (not the 100-row tail), it surfaces matches buried
	// well beyond that window. `null` = the default all-statuses tail.
	const JOB_FILTERS: { label: string; value: string | null }[] = [
		{ label: 'All', value: null },
		{ label: 'Pending', value: 'pending' },
		{ label: 'Backoff', value: 'backoff' },
		{ label: 'Completed', value: 'completed' },
		{ label: 'Failed', value: 'failed' }
	];
	let jobFilter = $state<string | null>(null);

	// Server row caps (mirror collectQueueStatus): 100 for the live tail, 250 for a
	// filtered lookup. At the cap there may be more matches than shown — surface a
	// "+" so the count doesn't read as exhaustive.
	const jobsCapped = $derived(recentJobs.length >= (jobFilter ? 250 : 100));

	// Polling state
	let lastRefreshed = $state(new Date());
	let refreshAgo = $state('just now');

	// Two cadences: the full snapshot (incl. heavy time-series/aggregate queries) on
	// a slow poll, and just the cheap fast-moving queue slice (jobs / counts /
	// workers) on a faster one — so a 15s job refresh doesn't re-run the expensive
	// dashboard aggregations.
	const FULL_POLL_MS = 60_000;
	const QUEUE_POLL_MS = 15_000;

	// The fast queue slice (counts / jobs / workers) — owns the recent-jobs table
	// so it can honour the active status filter. Used by the poll interval and
	// re-run immediately when the filter changes.
	async function refreshQueue(filter: string | null = jobFilter) {
		try {
			const url = filter
				? `/api/status/queue?status=${encodeURIComponent(filter)}`
				: '/api/status/queue';
			const res = await fetch(url);
			if (!res.ok) return;
			const fresh = await res.json();
			queueStats = fresh.queueStats;
			recentJobs = fresh.recentJobs;
			workers = fresh.workers;
			lastRefreshed = new Date();
		} catch {
			/* silent */
		}
	}

	$effect(() => {
		const interval = setInterval(async () => {
			try {
				const res = await fetch('/api/status');
				if (!res.ok) return;
				const fresh = await res.json();
				hero = fresh.hero;
				contentBreakdown = fresh.contentBreakdown;
				modelBreakdown = fresh.modelBreakdown;
				contentLog = fresh.contentLog;
				queueStats = fresh.queueStats;
				workers = fresh.workers;
				// recentJobs is deliberately left to refreshQueue: the full snapshot's
				// list is the unfiltered tail and would clobber an active filter.
				lastRefreshed = new Date();
			} catch {
				/* silent */
			}
		}, FULL_POLL_MS);
		return () => clearInterval(interval);
	});

	$effect(() => {
		const interval = setInterval(refreshQueue, QUEUE_POLL_MS);
		return () => clearInterval(interval);
	});

	// Re-query immediately when the filter changes (don't wait for the next poll).
	// Reading jobFilter into a local both registers the reactive dependency and
	// passes the exact value to the fetch.
	$effect(() => {
		const filter = jobFilter;
		refreshQueue(filter);
	});

	// Update "refreshed Xs ago"
	$effect(() => {
		const tick = setInterval(() => {
			const secs = Math.floor((Date.now() - lastRefreshed.getTime()) / 1000);
			refreshAgo = secs < 5 ? 'just now' : `${secs}s ago`;
		}, 1000);
		return () => clearInterval(tick);
	});

	// ── Hero health state ──
	//
	// The hero header reflects how many jobs failed in the stat window. Below 10%
	// failed we're nominal; 10–25% is degraded; ≥25% is the "this is fine" (red)
	// everything-on-fire state.
	type Health = {
		word: string; // emphasised word in the headline
		lede: string; // text preceding it
		accent: string; // headline + tag color
		tagBg: string;
		tagBorder: string;
		tagLabel: string;
		dot: 'ok' | 'warn' | 'err';
	};

	const DEGRADED_THRESHOLD = 0.1;
	const CRITICAL_THRESHOLD = 0.25;

	const health = $derived.by<Health>(() => {
		const rate = hero?.failureRate ?? 0;
		if (rate >= CRITICAL_THRESHOLD) {
			return {
				lede: 'This is',
				word: 'fine',
				accent: 'var(--danger)',
				tagBg: 'rgba(184, 85, 67, 0.12)',
				tagBorder: 'var(--danger)',
				tagLabel: 'Critical',
				dot: 'err'
			};
		}
		if (rate >= DEGRADED_THRESHOLD) {
			return {
				lede: 'Error rate',
				word: 'warning',
				accent: 'var(--warn)',
				tagBg: 'rgba(196, 154, 56, 0.12)',
				tagBorder: 'var(--warn)',
				tagLabel: 'Degraded',
				dot: 'warn'
			};
		}
		return {
			lede: 'All systems',
			word: 'nominal',
			accent: 'var(--teal-2)',
			tagBg: 'var(--sage-2)',
			tagBorder: 'var(--sage)',
			tagLabel: 'Healthy',
			dot: 'ok'
		};
	});

	const failurePct = $derived(hero ? Math.round(hero.failureRate * 100) : 0);

	// Derived
	const totalPending = $derived(queueStats ? queueStats.queued + queueStats.backoff : 0);
	const maxBreakdownCount = $derived(Math.max(...contentBreakdown.map((r) => r.count), 1));
	const maxModelCount = $derived(Math.max(...modelBreakdown.map((r) => r.count), 1));

	const _priColor: Record<number, string> = {
		10: 'var(--danger)',
		5: 'var(--ink-2)',
		1: 'var(--ink-4)',
		0: 'var(--ink-4)'
	};

	function priColorFor(p: number): string {
		if (p == 0) return 'var(--ink)';
		if (p >= 2) return 'var(--ink-4)';
		if (p >= 3) return 'var(--paper-2)';
		return 'var(--paper)';
	}

	const STATUS_COLORS: Record<string, string> = {
		pending: 'var(--ink-2)',
		in_progress: '#3d8bff',
		backoff: 'var(--gold)',
		completed: 'var(--teal-2)',
		failed: 'var(--danger)',
		cancelled: 'var(--ink-4)'
	};
	const statusColor = (s: string): string => STATUS_COLORS[s] ?? 'var(--ink-3)';

	// Compact duration: 42s · 18min42s · 1h18min
	function formatDuration(seconds: number): string {
		const s = Math.round(seconds);
		if (s < 60) return `${s}s`;
		const h = Math.floor(s / 3600);
		const m = Math.floor((s % 3600) / 60);
		const rem = s % 60;
		if (h > 0) return m > 0 ? `${h}h${m}min` : `${h}h`;
		return rem > 0 ? `${m}min${rem}s` : `${m}min`;
	}
</script>

<svelte:head>
	<title>Operations Status - Symbology</title>
	<meta name="description" content="System health and operations dashboard" />
</svelte:head>

<!-- Sub-nav -->
<StatusNav active="Overview" {refreshAgo} />

<div style="height: 2rem;"></div>

<!-- ═══════════ HERO ═══════════ -->
<section class="two-col-even" style="align-items: end;">
	<div>
		<div class="eyebrow" style="margin-bottom: 1.125rem;">
			<span style="color: {health.accent};">&#9679;</span>&nbsp;&nbsp;OPERATIONS &middot; status
		</div>
		{#if hero}
			<h1 class="display" style="margin-bottom: 1.125rem; font-size: 3.5rem;">
				{health.lede} <span style="color: {health.accent};">{health.word}</span>.
			</h1>
			<!-- Editorial note: what the pipeline is working on (see $lib/status-message). -->
			<div style="max-width: 34rem;">
				<div class="meta" style="margin-bottom: 0.375rem; color: var(--ink-4);">
					{STATUS_MESSAGE.date}
				</div>
				<div
					style="font-family: var(--serif); font-size: 1.0625rem; color: var(--ink); letter-spacing: -0.01em; margin-bottom: 0.375rem;"
				>
					{STATUS_MESSAGE.headline}
				</div>
				<p style="font-size: 0.8125rem; line-height: 1.55; color: var(--ink-3); margin: 0;">
					{STATUS_MESSAGE.body}
				</p>
			</div>
			<div style="display: flex; gap: 0.875rem; margin-top: 1.375rem; align-items: center;">
				<span
					class="tag"
					style="display: inline-flex; align-items: center; gap: 0.5rem; background: {health.tagBg}; border-color: {health.tagBorder}; color: {health.accent};"
				>
					<StatusDot kind={health.dot} />
					{health.tagLabel}
				</span>
				<span class="meta" style="color: var(--ink-4);">
					{failurePct}% failed &middot; {stat_window}hr
				</span>
			</div>
		{:else}
			<h1 class="display" style="margin-bottom: 1.125rem;">Status unavailable</h1>
			<p class="lede">Could not load system status.</p>
		{/if}
	</div>
	{#if hero}
		<div class="grid grid-cols-2 md:grid-cols-3" style="gap: 0;">
			<div class="stat" style="padding: 1rem 0; ">
				<span class="stat-label">Workers online</span>
				<span class="stat-value" style="font-size: 2rem;">{hero.workersOnline} </span>
			</div>
			<div class="stat" style="padding: 1rem 0;">
				<span class="stat-label">Completed jobs &middot; {stat_window}hr</span>
				<span class="stat-value" style="font-size: 2rem;">{hero.completedCount}</span>
			</div>
			<div class="stat" style="padding: 1rem 0;">
				<span class="stat-label">p95 job duration</span>
				<span class="stat-value" style="font-size: 2rem;">
					{hero.p95JobDuration != null ? formatDuration(hero.p95JobDuration) : '—'}
				</span>
			</div>
			<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
				<span class="stat-label flex items-center gap-1">
					LLM spend &middot; {stat_window}hr
				</span>
				<span class="stat-value" style="font-size: 2rem;">${hero.llmSpend.toFixed(2)}</span>
				<span class="" style="color: var(--ink-4);"
					>Estimated

					<span
						class="spec-help"
						title={HOST_SPECS}
						style="display: inline-flex; align-items: center; color: var(--ink-4); cursor: help;"
					>
						<CircleQuestionMark class="size-3" />
					</span>
				</span>
			</div>
			<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
				<span class="stat-label">Generations &middot; {stat_window}hr</span>
				<span class="stat-value" style="font-size: 2rem;">{hero.generationsCount}</span>
			</div>
			<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
				<span class="stat-label">p95 LLM latency</span>
				<span class="stat-value" style="font-size: 2rem;">
					{hero.p95Latency != null ? `${hero.p95Latency}s` : '—'}
				</span>
			</div>
		</div>
	{/if}
</section>

<!-- ═══════════ JOB QUEUE ═══════════ -->
<section class="hairline-section" id="queue">
	<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
		<div>
			<div class="eyebrow" style="margin-bottom: 0.625rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;JOB QUEUE
			</div>
			<h2 class="section-heading">In flight, queued, retrying.</h2>
		</div>
	</div>

	<div class="grid-2" style="align-items: start; gap: 1.5rem; margin-bottom: 2.25rem;">
		<!-- Right now stats -->
		{#if queueStats}
			<div class="" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Right now</h3>
					<span class="meta">{totalPending} pending &middot; {queueStats.running} running</span>
				</div>
				<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem;">
					{#each [{ k: 'Running', v: queueStats.running, c: '#3d8bff', sub: '' }, { k: 'Queued', v: queueStats.queued, c: 'var(--ink-2)', sub: 'FIFO within priority' }, { k: 'Backoff', v: queueStats.backoff, c: 'var(--warn)', sub: 'deps / retry wait' }, { k: `Failed · ${stat_window}hr`, v: queueStats.failedInWindow, c: 'var(--danger)', sub: 'dead-letter' }] as s (s.k)}
						<div
							style="padding: 1rem 1.125rem; border: 1px solid var(--rule); border-radius: 10px;"
						>
							<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
								<span style="width: 8px; height: 8px; background: {s.c}; border-radius: 999px;"
								></span>
								<span class="meta">{s.k}</span>
							</div>
							<div
								style="font-family: var(--serif); font-size: 1.75rem; color: var(--ink); letter-spacing: -0.01em; line-height: 1;"
							>
								{s.v}
							</div>
							<div style="font-size: 0.71875rem; color: var(--ink-4); margin-top: 0.375rem;">
								{s.sub}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Generated content by kind -->
		{#if contentBreakdown.length > 0}
			<div class="" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Generated content &middot; by kind</h3>
					<span class="meta text-xs" style="color: var(--ink-4);">count latency cost</span>
				</div>
				<div style="display: flex; flex-direction: column; gap: 0.875rem;">
					{#each contentBreakdown.slice(0, 6) as r (r.kind)}
						<div
							style="display: grid; grid-template-columns: 1fr 60px 50px 50px; gap: 1rem; align-items: center;"
						>
							<div>
								<div style="font-size: 0.84375rem; color: var(--ink); margin-bottom: 0.25rem;">
									{r.kind}
								</div>
								<Bar value={r.count} max={maxBreakdownCount} color="var(--teal-2)" />
							</div>
							<span class="mono-sm" style="text-align: right;">{r.count}</span>
							<span class="mono-sm muted" style="text-align: right;">{r.avgLatency}</span>
							<span class="mono-sm" style="text-align: right; color: var(--ink-3);"
								>{r.totalCost}</span
							>
						</div>
					{/each}
				</div>

				<!-- Generated content by model -->
				{#if modelBreakdown.length > 0}
					<div style="margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid var(--rule);">
						<div class="flex-between" style="margin-bottom: 1.125rem;">
							<h3 class="sub">By model</h3>
							<span class="meta text-xs" style="color: var(--ink-4);">count latency cost</span>
						</div>
						<div style="display: flex; flex-direction: column; gap: 0.875rem;">
							{#each modelBreakdown.slice(0, 6) as r (r.model)}
								<div
									style="display: grid; grid-template-columns: 1fr 60px 50px 50px; gap: 1rem; align-items: center;"
								>
									<div style="min-width: 0;">
										<div
											style="font-size: 0.84375rem; color: var(--ink); margin-bottom: 0.25rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
											title={r.model}
										>
											{r.model}
										</div>
										<Bar value={r.count} max={maxModelCount} color="var(--gold)" />
									</div>
									<span class="mono-sm" style="text-align: right;">{r.count}</span>
									<span class="mono-sm muted" style="text-align: right;">{r.avgLatency}</span>
									<span class="mono-sm" style="text-align: right; color: var(--ink-3);"
										>{r.totalCost}</span
									>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Recent jobs table (mirrors `jobs list`) -->
	<div class="status-card">
		<div style="padding: 1rem 1.5rem; border-bottom: 1px solid var(--rule);" class="flex-between">
			<h3 class="sub">
				Recent jobs &middot; {recentJobs.length}{#if jobsCapped}<span style="color: var(--ink-4);"
						>+</span
					>{/if}
			</h3>
			<!-- Status filters. A non-"All" filter triggers a deliberate server query
			     that reaches past the default 100-row tail (see refreshQueue). -->
			<div class="filter-chips" role="group" aria-label="Filter jobs by status">
				{#each JOB_FILTERS as f (f.label)}
					<button
						type="button"
						class="filter-chip"
						class:active={jobFilter === f.value}
						onclick={() => (jobFilter = f.value)}
					>
						{f.label}
					</button>
				{/each}
			</div>
		</div>
		{#if recentJobs.length > 0}
			<div class="table-scroll scroll-y">
				<table class="status-table">
					<thead>
						<tr>
							<th style="width: 24px; text-align: center;">P</th>
							<th>ID</th>
							<th>Type</th>
							<th>Context</th>
							<th>Status</th>
							<th style="text-align: right;">Try</th>
							<th style="text-align: right;">Worker</th>
							<th style="text-align: right;">When</th>
						</tr>
					</thead>
					<tbody>
						{#each recentJobs as j, i (j.id)}
							<tr class:last={i === recentJobs.length - 1}>
								<td style="padding: 0.6875rem 0; text-align: center;">
									<span
										style="display: inline-block; width: 3px; height: 26px; background: {priColorFor(
											j.priority
										)}; border-radius: 1.5px;"
									></span>
								</td>
								<td class="mono-cell">{j.shortId}</td>
								<td class="mono-cell" style="color: var(--ink-2);">{j.type}</td>
								<td class="mono-cell">{j.context}</td>
								<td>
									<span
										class="status-badge"
										style="color: {statusColor(j.status)}; white-space: nowrap;"
									>
										<span
											style="display: inline-block; width: 6px; height: 6px; border-radius: 9999px; background: {statusColor(
												j.status
											)};"
										></span>
										{j.status}
									</span>
								</td>
								<td
									class="mono-cell"
									style="text-align: right; color: {j.attempt.startsWith('1')
										? 'var(--ink-3)'
										: 'var(--warn)'};"
								>
									{j.attempt}
								</td>
								<td class="mono-cell" style="text-align: right;">{j.worker}</td>
								<td class="mono-cell" style="text-align: right; white-space: nowrap;">{j.when}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div style="padding: 2.5rem 1.5rem; text-align: center; color: var(--ink-4);" class="meta">
				No {jobFilter ? `${jobFilter.replace('_', ' ')} ` : ''}jobs.
			</div>
		{/if}
	</div>
</section>

<!-- ═══════════ GENERATED CONTENT ═══════════ -->
<section class="hairline-section" id="generations">
	<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
		<div>
			<div class="eyebrow" style="margin-bottom: 0.625rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;LLM PIPELINE
			</div>
			<h2 class="section-heading">Generated content, live.</h2>
		</div>
	</div>

	<!-- Generation log -->
	{#if contentLog.length > 0}
		<div class="status-card">
			<div style="padding: 1rem 1.5rem; border-bottom: 1px solid var(--rule);" class="flex-between">
				<h3 class="sub">Generation log &middot; {contentLog.length}</h3>
				<span class="meta" style="display: inline-flex; align-items: center; gap: 0.5rem;">
					<BlinkDot color="var(--teal-2)" /> streaming
				</span>
			</div>
			<div class="table-scroll scroll-y">
				<table class="status-table">
					<thead>
						<tr>
							<th>Time</th>
							<th>ID</th>
							<th>Kind</th>
							<th>Company</th>
							<th>Context</th>
							<th>Model</th>
							<th style="text-align: right;">Tok in / out</th>
							<th style="text-align: right;">Lat</th>
							<th style="text-align: right;">Cost</th>
							<th style="text-align: right;">Status</th>
						</tr>
					</thead>
					<tbody>
						{#each contentLog as r, i (i)}
							<tr
								class:last={i === contentLog.length - 1}
								class:row-fail={r.status === 'fail'}
								class:linked={!!r.href}
								role={r.href ? 'link' : undefined}
								tabindex={r.href ? 0 : undefined}
								onclick={() => r.href && goto(r.href)}
								onkeydown={(e) => {
									if (r.href && (e.key === 'Enter' || e.key === ' ')) {
										e.preventDefault();
										goto(r.href);
									}
								}}
							>
								<td class="mono-cell">{r.time}</td>
								<td class="mono-cell">{r.shortId}</td>
								<td style="font-size: 0.8125rem; color: var(--ink-2);">{r.kind}</td>
								<td class="mono-cell">{r.company}</td>
								<td class="mono-cell">{r.context}</td>
								<td class="mono-cell" style="font-size: 0.71875rem;">{r.model}</td>
								<td class="mono-cell" style="text-align: right;">
									{r.tokensIn.toLocaleString()} / {r.tokensOut.toLocaleString()}
								</td>
								<td class="mono-cell" style="text-align: right;">{r.latency}</td>
								<td class="mono-cell" style="text-align: right;">{r.cost}</td>
								<td style="text-align: right;">
									<span
										class="status-badge"
										class:status-ok={r.status === 'ok'}
										class:status-err={r.status === 'fail'}
										class:status-warn={r.status === 'retry'}
									>
										<StatusDot
											kind={r.status === 'ok' ? 'ok' : r.status === 'fail' ? 'err' : 'warn'}
											size={6}
										/>
										{r.status}
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</section>

<!-- ═══════════ WORKERS ═══════════ -->
{#if workers.length > 0}
	<section class="hairline-section" id="workers">
		<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
			<div>
				<div class="eyebrow" style="margin-bottom: 0.625rem;">
					<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;WORKER POOL
				</div>
				<h2 class="section-heading">
					{workers.length} workers, {workers.filter((w) => w.status === 'running').length} active.
				</h2>
			</div>
		</div>

		<div class="status-card">
			<div style="padding: 1rem 1.5rem; border-bottom: 1px solid var(--rule);" class="flex-between">
				<h3 class="sub">Workers &middot; {workers.length}</h3>
				<span class="meta">{workers.filter((w) => w.status === 'running').length} active</span>
			</div>
			<div class="table-scroll scroll-y">
				<table class="status-table">
					<thead>
						<tr>
							<th>Worker</th>
							<th>Current job</th>
							<th>Context</th>
							<th style="text-align: right;">Elapsed</th>
							<th style="text-align: right;">Throughput</th>
							<th style="text-align: right;">Status</th>
						</tr>
					</thead>
					<tbody>
						{#each workers as w, i (w.id)}
							<tr class:last={i === workers.length - 1}>
								<td class="mono-cell" style="color: var(--ink-2);">{w.id}</td>
								<td class="mono-cell">
									{#if w.job === '—'}
										<span style="color: var(--ink-4); font-style: italic;"
											>awaiting next claim&hellip;</span
										>
									{:else}
										{w.job}
									{/if}
								</td>
								<td class="mono-cell">
									{#if w.context === '—'}
										<span style="color: var(--ink-4);">—</span>
									{:else}
										{w.context}
									{/if}
								</td>
								<td class="mono-cell" style="text-align: right;">
									{w.status === 'running' ? w.elapsed : '—'}
								</td>
								<td class="mono-cell" style="text-align: right;">{w.rate}</td>
								<td style="text-align: right;">
									<span
										class="status-badge"
										style="color: {w.status === 'running' ? '#3d8bff' : 'var(--ink-3)'};"
									>
										<span
											style="display: inline-block; width: 6px; height: 6px; border-radius: 9999px; background: {w.status ===
											'running'
												? '#3d8bff'
												: 'var(--ink-4)'};"
										></span>
										{w.status}
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</section>
{/if}

<style>
	/* ── Card surface ── */
	.status-card {
		border: 1px solid var(--rule);
		border-radius: 10px;
		background: var(--paper);
	}

	/* Wide dense tables scroll horizontally instead of overflowing the page. */
	.table-scroll {
		overflow-x: auto;
	}
	/* Dense log tables scroll vertically through many rows with a pinned header. */
	.scroll-y {
		max-height: 30rem;
		overflow-y: auto;
	}
	.scroll-y thead th {
		position: sticky;
		top: 0;
		background: var(--paper);
		z-index: 1;
	}

	/* ── Dense table ── */
	.status-table {
		width: 100%;
		border-collapse: collapse;
	}
	.status-table th {
		text-align: left;
		padding: 0.75rem 1.25rem;
		font-family: var(--mono);
		font-size: 0.65625rem;
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--ink-3);
		border-bottom: 1px solid var(--rule);
	}
	.status-table td {
		padding: 0.6875rem 1.25rem;
	}
	.status-table tbody tr {
		border-bottom: 1px solid var(--rule);
	}
	.status-table tbody tr.last {
		border-bottom: 0;
	}
	.status-table tbody tr.linked {
		cursor: pointer;
	}
	.status-table tbody tr.linked:hover {
		background: var(--sage-2);
	}

	/* ── Cell helpers ── */
	.mono-cell {
		font-family: var(--mono);
		font-size: 0.75rem;
		color: var(--ink-3);
	}
	.mono-sm {
		font-family: var(--mono);
		font-size: 0.75rem;
		color: var(--ink);
	}
	.mono-sm.muted {
		color: var(--ink-4);
	}

	/* ── Status badges ── */
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		font-family: var(--mono);
		font-size: 0.6875rem;
	}
	.status-ok {
		color: var(--teal-2);
	}
	.status-err {
		color: var(--danger);
	}
	.status-warn {
		color: var(--warn);
	}

	/* ── Failed row highlight ── */
	.row-fail {
		background: rgba(184, 85, 67, 0.04);
	}

	/* ── Status filter chips ── */
	.filter-chips {
		display: flex;
		gap: 0.375rem;
		flex-wrap: wrap;
	}
	.filter-chip {
		font-family: var(--mono);
		font-size: 0.6875rem;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--ink-3);
		background: transparent;
		border: 1px solid var(--rule);
		border-radius: 999px;
		padding: 0.25rem 0.75rem;
		cursor: pointer;
		transition:
			color 0.12s ease,
			border-color 0.12s ease,
			background 0.12s ease;
	}
	.filter-chip:hover {
		color: var(--ink);
		border-color: var(--ink-4);
	}
	.filter-chip.active {
		color: var(--paper);
		background: var(--ink);
		border-color: var(--ink);
	}

	/* ── Responsive ── */
	@media (max-width: 768px) {
		.grid-2 {
			grid-template-columns: 1fr;
		}
	}
</style>
