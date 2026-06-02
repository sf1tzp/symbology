<script lang="ts">
	import { CircleQuestionMark } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import type {
		HeroStats,
		IngestionDayRow,
		RecentFilingRow,
		ContentBreakdownRow,
		ThroughputDayRow,
		ContentLogRow,
		JobQueueStats,
		QueueDepthPoint,
		ActiveJobRow,
		WorkerRow
	} from '$lib/server/db/status';
	import StatusDot from '$lib/components/status/StatusDot.svelte';
	import BlinkDot from '$lib/components/status/BlinkDot.svelte';
	import Bar from '$lib/components/status/Bar.svelte';
	import StackedColumns from '$lib/components/status/StackedColumns.svelte';
	import AreaChart from '$lib/components/status/AreaChart.svelte';
	import StatusNav from '$lib/components/status/StatusNav.svelte';

	let { data }: { data: PageData } = $props();

	// Self-hosting brag — surfaced via the spend tooltip.
	const HOST_SPECS =
		'The majority of content is generated on consumer hardware ' +
		'(Apple M3 Macbook Air 24GB, Nvidia 3060 12GB), which we estimate ~$0.02/hr of compute. ' +
		'Self-hosted generations are metered by compute time at that rate; Claude API calls are counted at Anthropic per-token rates.';

	// Mutable state for polling
	let hero = $state<HeroStats | null>(data.hero);
	let ingestionDays = $state<IngestionDayRow[]>(data.ingestionDays);
	let recentFilings = $state<RecentFilingRow[]>(data.recentFilings);
	let contentBreakdown = $state<ContentBreakdownRow[]>(data.contentBreakdown);
	let contentThroughput = $state<ThroughputDayRow[]>(data.contentThroughput);
	let contentLog = $state<ContentLogRow[]>(data.contentLog);
	let queueStats = $state<JobQueueStats | null>(data.queueStats);
	let queueDepth = $state<QueueDepthPoint[]>(data.queueDepth);
	let activeJobs = $state<ActiveJobRow[]>(data.activeJobs);
	let workers = $state<WorkerRow[]>(data.workers);

	// Polling state
	let lastRefreshed = $state(new Date());
	let refreshAgo = $state('just now');

	// Poll every 10s
	$effect(() => {
		const interval = setInterval(async () => {
			try {
				const res = await fetch('/api/status');
				if (res.ok) {
					const fresh = await res.json();
					hero = fresh.hero;
					ingestionDays = fresh.ingestionDays;
					recentFilings = fresh.recentFilings;
					contentBreakdown = fresh.contentBreakdown;
					contentThroughput = fresh.contentThroughput;
					contentLog = fresh.contentLog;
					queueStats = fresh.queueStats;
					queueDepth = fresh.queueDepth;
					activeJobs = fresh.activeJobs;
					workers = fresh.workers;
					lastRefreshed = new Date();
				}
			} catch {
				/* silent */
			}
		}, 10_000);
		return () => clearInterval(interval);
	});

	// Update "refreshed Xs ago"
	$effect(() => {
		const tick = setInterval(() => {
			const secs = Math.floor((Date.now() - lastRefreshed.getTime()) / 1000);
			refreshAgo = secs < 5 ? 'just now' : `${secs}s ago`;
		}, 1000);
		return () => clearInterval(tick);
	});

	// Derived
	const totalPending = $derived(queueStats ? queueStats.queued + queueStats.backoff : 0);
	const maxBreakdownCount = $derived(Math.max(...contentBreakdown.map((r) => r.count), 1));
	const throughputAvg = $derived(
		contentThroughput.length > 0
			? Math.round(contentThroughput.reduce((s, d) => s + d.v, 0) / contentThroughput.length)
			: 0
	);

	// Filing legend totals
	const ingestionTotals = $derived({
		k: ingestionDays.reduce((s, d) => s + d.k, 0),
		q: ingestionDays.reduce((s, d) => s + d.q, 0),
		_8k: ingestionDays.reduce((s, d) => s + d._8k, 0),
		other: ingestionDays.reduce((s, d) => s + d.other, 0)
	});

	const _priColor: Record<number, string> = {
		10: 'var(--danger)',
		5: 'var(--ink-2)',
		1: 'var(--ink-4)',
		0: 'var(--ink-4)'
	};

	function priColorFor(p: number): string {
		if (p >= 10) return 'var(--danger)';
		if (p >= 5) return 'var(--ink-2)';
		return 'var(--ink-4)';
	}

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
<section style="display: grid; grid-template-columns: 1fr 1fr; gap: 4rem; align-items: end;">
	<div>
		<div class="eyebrow" style="margin-bottom: 1.125rem;">
			<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;OPERATIONS &middot; status
		</div>
		{#if hero}
			<h1 class="display" style="margin-bottom: 1.125rem; font-size: 3.5rem;">
				All systems <span style="color: var(--teal-2);">nominal</span>.
			</h1>
			<p class="lede">
				Ingestion is on schedule, the worker pool is healthy, and the LLM pipeline is processing
				within budget. {queueStats?.running ?? 0} jobs currently in flight,
				{totalPending} queued.
			</p>
			<div style="display: flex; gap: 0.875rem; margin-top: 1.375rem; align-items: center;">
				<span
					class="tag"
					style="display: inline-flex; align-items: center; gap: 0.5rem; background: var(--sage-2); border-color: var(--sage); color: var(--teal-2);"
				>
					<StatusDot kind="ok" /> Healthy
				</span>
			</div>
		{:else}
			<h1 class="display" style="margin-bottom: 1.125rem;">Status unavailable</h1>
			<p class="lede">Could not load system status.</p>
		{/if}
	</div>
	{#if hero}
		<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0;">
			<div class="stat" style="padding: 1rem 0; ">
				<span class="stat-label">Workers online</span>
				<span class="stat-value" style="font-size: 2rem;">{hero.workersOnline} </span>
			</div>
			<div class="stat" style="padding: 1rem 0;">
				<span class="stat-label">Completed jobs &middot; 12hr</span>
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
					LLM spend &middot; 12hr
					<span
						class="spec-help"
						title={HOST_SPECS}
						style="display: inline-flex; align-items: center; color: var(--ink-4); cursor: help;"
					>
						<CircleQuestionMark style="width: 11px; height: 11px;" />
					</span>
				</span>
				<span class="stat-value" style="font-size: 2rem;">${hero.llmSpend.toFixed(2)}</span>
				<span class="meta" style="color: var(--ink-3);">${hero.avgCostPerGen.toFixed(3)} / gen</span
				>
			</div>
			<div class="stat" style="padding: 1rem 0; border-top: 1px solid var(--rule);">
				<span class="stat-label">Generations &middot; 12hr</span>
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
		<!-- Depth chart -->
		{#if queueDepth.length > 0}
			<div class="status-card" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Depth &middot; last 24h</h3>
					<span class="meta">peak {Math.max(...queueDepth.map((d) => d.v))}</span>
				</div>
				<AreaChart data={queueDepth} color="var(--ink-2)" height={170} />
			</div>
		{/if}

		<!-- Right now stats -->
		{#if queueStats}
			<div class="status-card" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Right now</h3>
					<span class="meta">{totalPending} pending &middot; {queueStats.running} running</span>
				</div>
				<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem;">
					{#each [{ k: 'Running', v: queueStats.running, c: '#3d8bff', sub: '' }, { k: 'Queued', v: queueStats.queued, c: 'var(--ink-2)', sub: 'FIFO within priority' }, { k: 'Scheduled', v: queueStats.backoff, c: 'var(--warn)', sub: 'Not Implemented' }, { k: 'Failed · 24h', v: queueStats.failed24h, c: 'var(--danger)', sub: 'dead-letter' }] as s (s.k)}
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
	</div>

	<!-- Active jobs table -->
	{#if activeJobs.length > 0}
		<div class="status-card">
			<div style="padding: 1rem 1.5rem; border-bottom: 1px solid var(--rule);" class="flex-between">
				<h3 class="sub">In-flight & queued &middot; {activeJobs.length}</h3>
			</div>
			<table class="status-table">
				<thead>
					<tr>
						<th style="width: 24px; text-align: center;"></th>
						<th>Job ID</th>
						<th>Kind</th>
						<th>Company</th>
						<th>Target</th>
						<th style="text-align: right;">Try</th>
						<th style="text-align: right;">Worker</th>
						<th style="text-align: right;">Runtime</th>
						<th style="text-align: right;">State</th>
					</tr>
				</thead>
				<tbody>
					{#each activeJobs as j, i (j.id)}
						<tr class:last={i === activeJobs.length - 1}>
							<td style="padding: 0.6875rem 0; text-align: center;">
								<span
									style="display: inline-block; width: 3px; height: 26px; background: {priColorFor(
										j.priority
									)}; border-radius: 1.5px;"
								></span>
							</td>
							<td class="mono-cell">{j.id}</td>
							<td class="mono-cell" style="color: var(--ink-2);">{j.kind}</td>
							<td class="mono-cell">{j.company}</td>
							<td class="serif-cell">{j.target}</td>
							<td
								class="mono-cell"
								style="text-align: right; color: {j.attempt.startsWith('1')
									? 'var(--ink-3)'
									: 'var(--warn)'};"
							>
								{j.attempt}
							</td>
							<td class="mono-cell" style="text-align: right;">{j.workerId}</td>
							<td class="mono-cell" style="text-align: right;">{j.runtime}</td>
							<td style="text-align: right;">
								{#if j.state === 'running'}
									<span class="status-badge" style="color: #3d8bff;">
										<BlinkDot color="#3d8bff" /> running
									</span>
								{:else if j.state === 'backoff'}
									<span class="status-badge status-warn">
										<StatusDot kind="warn" size={6} /> backoff
									</span>
								{:else}
									<span class="status-badge status-idle">
										<StatusDot kind="idle" size={6} /> queued
									</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<!-- ═══════════ GENERATED CONTENT ═══════════ -->
<section class="hairline-section" id="generations">
	<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
		<div>
			<div class="eyebrow" style="margin-bottom: 0.625rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;LLM PIPELINE
			</div>
			<h2 class="section-heading">Generated content, by kind.</h2>
		</div>
	</div>

	<div class="grid-2" style="align-items: start; gap: 1.5rem;">
		<!-- Breakdown -->
		{#if contentBreakdown.length > 0}
			<div class="status-card" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Mix &middot; last 24h</h3>
					<span class="meta">{contentBreakdown.reduce((s, r) => s + r.count, 0)} total</span>
				</div>
				<div style="display: flex; flex-direction: column; gap: 0.875rem;">
					{#each contentBreakdown as r (r.kind)}
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
				<div
					class="flex-between"
					style="margin-top: 1.125rem; padding-top: 0.875rem; border-top: 1px solid var(--rule);"
				>
					<span class="meta" style="color: var(--ink-4);"
						>count &middot; avg latency &middot; total cost · 24h</span
					>
				</div>
			</div>
		{/if}

		<!-- Throughput chart -->
		{#if contentThroughput.length > 0}
			<div class="status-card" style="padding: 1.75rem;">
				<div class="flex-between" style="margin-bottom: 1.125rem;">
					<h3 class="sub">Throughput &middot; 14 days</h3>
					<span class="meta">avg {throughputAvg} / day</span>
				</div>
				<AreaChart data={contentThroughput} color="var(--teal-2)" height={180} />
			</div>
		{/if}
	</div>

	<!-- Generation log -->
	{#if contentLog.length > 0}
		<div style="margin-top: 2.25rem;">
			<div class="flex-between" style="margin-bottom: 0.875rem; align-items: baseline;">
				<h3 class="sub">Generation log</h3>
				<span class="meta" style="display: inline-flex; align-items: center; gap: 0.5rem;">
					<BlinkDot color="var(--teal-2)" /> streaming &middot; {contentLog.length} recent
				</span>
			</div>
			<div class="status-card">
				<table class="status-table">
					<thead>
						<tr>
							<th>Time</th>
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
								<td style="font-size: 0.8125rem; color: var(--ink-2);">{r.kind}</td>
								<td class="mono-cell">{r.company}</td>
								<td class="serif-cell">{r.context}</td>
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

		<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
			{#each workers as w (w.id)}
				<div
					class="status-card"
					style="padding: 1.375rem; border-left: {w.status === 'running'
						? '3px solid var(--teal-2)'
						: '1px solid var(--rule)'};"
				>
					<div class="flex-between" style="margin-bottom: 0.875rem; align-items: flex-start;">
						<div>
							<div
								style="display: flex; align-items: center; gap: 0.625rem; margin-bottom: 0.25rem;"
							>
								<span
									style="font-family: var(--serif); font-size: 1.25rem; color: var(--ink); letter-spacing: -0.01em;"
								>
									{w.id}
								</span>
							</div>
							<div style="display: flex; align-items: center; gap: 0.5rem;">
								{#if w.status === 'running'}
									<BlinkDot color="#3d8bff" />
									<span
										style="font-family: var(--mono); font-size: 0.6875rem; color: #3d8bff; text-transform: uppercase; letter-spacing: 0.08em;"
									>
										running
									</span>
								{:else}
									<StatusDot kind="idle" size={8} />
									<span
										style="font-family: var(--mono); font-size: 0.6875rem; color: var(--ink-4); text-transform: uppercase; letter-spacing: 0.08em;"
									>
										idle
									</span>
								{/if}
							</div>
						</div>
					</div>

					<div
						style="padding: 0.875rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);"
					>
						<div class="meta" style="margin-bottom: 0.375rem;">Current job</div>
						<div
							style="font-family: var(--serif); font-size: 0.9375rem; color: var(--ink); min-height: 1.375rem;"
						>
							{#if w.job === '—'}
								<span style="color: var(--ink-4); font-style: italic;"
									>awaiting next claim&hellip;</span
								>
							{:else}
								{w.job}
							{/if}
						</div>
					</div>

					<div
						style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.875rem;"
					>
						<div>
							<div class="meta" style="color: var(--ink-4);">Throughput</div>
							<span style="font-family: var(--mono); font-size: 0.8125rem; color: var(--ink);"
								>{w.rate}</span
							>
						</div>
						{#if w.status === 'running'}
							<div>
								<div class="meta" style="color: var(--ink-4);">Elapsed</div>
								<span style="font-family: var(--mono); font-size: 0.8125rem; color: var(--ink);"
									>{w.elapsed}</span
								>
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</section>
{/if}

<!-- ═══════════ INGESTION ═══════════ -->
<section class="hairline-section" id="ingestion">
	<div class="flex-between" style="align-items: flex-end; margin-bottom: 1.75rem;">
		<div>
			<div class="eyebrow" style="margin-bottom: 0.625rem;">
				<span style="color: var(--teal-2);">&#9679;</span>&nbsp;&nbsp;EDGAR INGESTION
			</div>
			<h2 class="section-heading">Filings, in by form type.</h2>
		</div>
	</div>

	{#if ingestionDays.length > 0}
		<div class="status-card" style="padding: 1.75rem;">
			<StackedColumns
				data={ingestionDays}
				segments={['k', 'q', '_8k', 'other']}
				colors={['var(--teal-2)', 'var(--olive)', 'var(--ink-2)', 'var(--ink-4)']}
				height={220}
			/>
			<div
				style="display: flex; gap: 1.75rem; margin-top: 0.875rem; padding-top: 1.125rem; border-top: 1px solid var(--rule); flex-wrap: wrap;"
			>
				{#each [{ c: 'var(--teal-2)', l: '10-K', v: ingestionTotals.k }, { c: 'var(--olive)', l: '10-Q', v: ingestionTotals.q }, { c: 'var(--ink-2)', l: '8-K', v: ingestionTotals._8k }, { c: 'var(--ink-4)', l: 'Other', v: ingestionTotals.other }] as legend (legend.l)}
					<span class="meta" style="display: flex; align-items: center; gap: 0.5rem;">
						<span style="width: 10px; height: 10px; background: {legend.c}; border-radius: 2px;"
						></span>
						{legend.l} &middot; <span style="color: var(--ink);">{legend.v}</span>
					</span>
				{/each}
				<span class="meta" style="margin-left: auto;">Source: EDGAR full-index</span>
			</div>
		</div>
	{/if}

	<!-- Recent pulls table -->
	{#if recentFilings.length > 0}
		<div style="margin-top: 2.25rem;">
			<div class="flex-between" style="margin-bottom: 0.875rem; align-items: baseline;">
				<h3 class="sub">Recent filings</h3>
				<span class="meta">Showing {recentFilings.length}</span>
			</div>
			<div class="status-card">
				<table class="status-table">
					<thead>
						<tr>
							<th>Time</th>
							<th>CIK</th>
							<th>Company</th>
							<th>Form</th>
							<th style="text-align: right;">Docs</th>
							<th style="text-align: right;">Status</th>
						</tr>
					</thead>
					<tbody>
						{#each recentFilings as r, i (i)}
							<tr class:last={i === recentFilings.length - 1}>
								<td class="mono-cell">{r.time}</td>
								<td class="mono-cell">{r.cik ?? '—'}</td>
								<td class="serif-cell">{r.company}</td>
								<td><span class="tag" style="font-size: 0.6875rem;">{r.form}</span></td>
								<td class="mono-cell" style="text-align: right;">{r.docCount || '—'}</td>
								<td style="text-align: right;">
									<span
										class="status-badge"
										class:status-ok={r.status === 'indexed'}
										class:status-idle={r.status !== 'indexed'}
									>
										<StatusDot kind={r.status === 'indexed' ? 'ok' : 'idle'} size={6} />
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

<!-- ═══════════ FOOTER ═══════════ -->
<footer
	style="margin-top: 5rem; padding-top: 1.75rem; border-top: 1px solid var(--rule); display: flex; justify-content: space-between; color: var(--ink-4);"
>
	<div class="meta">Operator console &middot; symbology-ops</div>
	<div class="meta">All times UTC &middot; auto-refresh 10s</div>
</footer>

<style>
	/* ── Card surface ── */
	.status-card {
		border: 1px solid var(--rule);
		border-radius: 10px;
		background: var(--paper);
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
	.serif-cell {
		font-family: var(--serif);
		font-size: 0.9375rem;
		color: var(--ink);
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
	.status-idle {
		color: var(--ink-3);
	}

	/* ── Failed row highlight ── */
	.row-fail {
		background: rgba(184, 85, 67, 0.04);
	}

	/* ── Responsive ── */
	@media (max-width: 768px) {
		.grid-2 {
			grid-template-columns: 1fr;
		}
	}
</style>
