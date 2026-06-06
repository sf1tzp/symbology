import { db } from '../db';
import { sql } from 'kysely';

// ── Generation cost model ──
//
// Claude models are billed per token at Anthropic API rates. Everything else
// runs on our own hardware — a single M3 MacBook Air we estimate at ~$0.01/hr
// of compute — so its cost is metered by generation wall-clock time, not tokens.

const COST_PER_INPUT_TOKEN: Record<string, number> = {
	'claude-sonnet-4-5-20250514': 3.0 / 1_000_000,
	'claude-haiku-4-5-20251001': 0.8 / 1_000_000
};
const COST_PER_OUTPUT_TOKEN: Record<string, number> = {
	'claude-sonnet-4-5-20250514': 15.0 / 1_000_000,
	'claude-haiku-4-5-20251001': 4.0 / 1_000_000
};
const DEFAULT_INPUT_COST = 3.0 / 1_000_000;
const DEFAULT_OUTPUT_COST = 15.0 / 1_000_000;

// Self-hosted compute estimate (M3 MacBook Air 70W + Nvidia 3060 170W = 240W ~= 0.04 per hour at 0.14 per kwh) .
export const SELF_HOST_COST_PER_HOUR = 0.04;
const SELF_HOST_COST_PER_SECOND = SELF_HOST_COST_PER_HOUR / 3600;

function isSelfHosted(model: string | null): boolean {
	return !(model ?? '').toLowerCase().startsWith('claude');
}

function generationCost(
	model: string | null,
	inputTokens: number | null,
	outputTokens: number | null,
	durationSeconds: number | null
): number {
	// Self-hosted models: meter by compute time at the M3 estimate.
	if (isSelfHosted(model)) {
		return (durationSeconds ?? 0) * SELF_HOST_COST_PER_SECOND;
	}
	// Claude models: Anthropic per-token API pricing.
	const m = model ?? '';
	const inCost = COST_PER_INPUT_TOKEN[m] ?? DEFAULT_INPUT_COST;
	const outCost = COST_PER_OUTPUT_TOKEN[m] ?? DEFAULT_OUTPUT_COST;
	return (inputTokens ?? 0) * inCost + (outputTokens ?? 0) * outCost;
}

// ── Label helpers ──

/** snake_case / lower-enum → Title Case, as a last-resort label. */
function humanize(s: string): string {
	return s
		.split('_')
		.filter(Boolean)
		.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
		.join(' ');
}

// Friendly names for the document sections content can be scoped to
// (DocumentType enum). Keeps the log readable instead of echoing raw enums.
const SECTION_LABELS: Record<string, string> = {
	management_discussion: 'MD&A',
	risk_factors: 'Risk factors',
	business_description: 'Business',
	controls_procedures: 'Controls & procedures',
	legal_proceedings: 'Legal proceedings',
	market_risk: 'Market risk',
	executive_compensation: 'Exec compensation',
	directors_officers: 'Directors & officers'
};

function sectionLabel(docType: string | null): string | null {
	if (!docType) return null;
	return SECTION_LABELS[docType] ?? humanize(docType);
}

function contentLabel(stage: string | null, docType: string | null): string {
	switch (stage) {
		// Prototype stages (being retired).
		case 'single_summary':
			return 'Document summary';
		case 'frontpage_summary':
			return 'Frontpage summary';
		case 'company_group_analysis':
			return 'Peer-group synthesis';
		case 'company_group_frontpage':
			return 'Group frontpage';
		case 'aggregate_summary':
			if (docType === 'risk_factors') return 'Risk-factor change analysis';
			if (docType === 'management_discussion') return 'MD&A change analysis';
			return 'Aggregate summary';
		// New page-content stages.
		case 'change_report':
			return 'Change report';
		case 'change_report_intro':
			return 'Change-report intro';
		case 'company_main_content':
			return 'Company page';
		case 'company_intro':
			return 'Company intro';
		case 'group_main_content':
			return 'Group page';
		case 'group_intro':
			return 'Group intro';
		case 'filing_main_content':
			return 'Filing page';
		case 'filing_intro':
			return 'Filing intro';
		case 'document_page_intro':
			return 'Document intro';
		default:
			return stage ? humanize(stage) : 'Unknown';
	}
}

// Friendly names for the worker job types shown in the in-flight queue.
const JOB_KIND_LABELS: Record<string, string> = {
	filing_page_content: 'Filing content',
	company_page_content: 'Company content',
	filing_ingestion: 'Filing ingest',
	company_ingestion: 'Company ingest',
	ingest_pipeline: 'Ingest pipeline',
	full_pipeline: 'Full pipeline',
	bulk_ingest: 'Bulk ingest',
	company_group_pipeline: 'Group pipeline',
	content_generation: 'Content gen'
};

function jobKindLabel(jobType: string): string {
	return JOB_KIND_LABELS[jobType] ?? humanize(jobType);
}

/**
 * Curate a job's heterogeneous params into a company + detail pair for display,
 * mirroring the server CLI's format_job_context so the two surfaces agree.
 */
function jobContext(
	jobType: string,
	params: Record<string, unknown> | null
): { company: string; detail: string } {
	const p = params ?? {};
	const str = (k: string) => (p[k] != null && p[k] !== '' ? String(p[k]) : null);
	const list = (k: string) => (Array.isArray(p[k]) ? (p[k] as unknown[]).map(String) : null);

	const ticker = str('ticker');
	let company = ticker ?? '—';
	let detailParts: (string | null)[] = [];

	switch (jobType) {
		case 'filing_page_content':
			detailParts = [str('form'), str('year') ? `FY${str('year')}` : null];
			break;
		case 'company_page_content':
			detailParts = [str('form'), str('lookback') ? `${str('lookback')} lookback` : null];
			break;
		case 'filing_ingestion':
		case 'ingest_pipeline':
			detailParts = [str('form'), str('count') ? `${str('count')}` : null];
			break;
		case 'full_pipeline': {
			const forms = list('forms');
			detailParts = [forms ? forms.join(', ') : null, p.force ? 'force' : null];
			break;
		}
		case 'company_group_pipeline': {
			const tickers = list('tickers');
			if (!ticker && tickers) company = tickers.join(', ');
			detailParts = [str('group_slug')];
			break;
		}
		case 'bulk_ingest': {
			const filings = list('filings');
			detailParts = [filings ? `${filings.length} filings` : null];
			break;
		}
	}

	if (company === '—' && p.company_id) {
		company = `Company ${String(p.company_id).slice(0, 8)}`;
	}

	return { company, detail: detailParts.filter(Boolean).join(' · ') || '—' };
}

// ── Types ──

export interface HeroStats {
	p95JobDuration: number | null;
	generationsCount: number;
	completedCount: number;
	workersOnline: number;
	totalWorkerSlots: number;
	llmSpend: number;
	avgCostPerGen: number;
	p95Latency: number | null;
}

export interface IngestionDayRow {
	label: string;
	k: number;
	q: number;
	_8k: number;
	other: number;
}

export interface RecentFilingRow {
	time: string;
	cik: string | null;
	company: string;
	form: string;
	docCount: number;
	status: 'indexed' | 'parsed' | 'pending';
}

export interface ContentBreakdownRow {
	kind: string;
	count: number;
	pct: string;
	avgLatency: string;
	totalCost: string;
}

export interface ThroughputDayRow {
	label: string;
	v: number;
}

export interface ContentLogRow {
	time: string;
	kind: string;
	company: string;
	context: string;
	href: string | null;
	model: string;
	tokensIn: number;
	tokensOut: number;
	latency: string;
	cost: string;
	status: 'ok' | 'retry' | 'fail';
}

export interface JobQueueStats {
	running: number;
	queued: number;
	backoff: number;
	failed24h: number;
}

export interface QueueDepthPoint {
	label: string;
	v: number;
}

export interface ActiveJobRow {
	id: string;
	/** First 10 chars of the id, for display only — NOT unique, never use as an {#each} key. */
	shortId: string;
	kind: string;
	priority: number;
	company: string;
	target: string;
	attempt: string;
	workerId: string;
	state: 'running' | 'queued' | 'backoff';
	runtime: string;
}

export interface WorkerRow {
	id: string;
	status: 'running' | 'idle';
	job: string;
	elapsed: string;
	rate: string;
}

// ── Queries ──

export async function getHeroStats(window: number): Promise<HeroStats> {
	const stat_window = sql<Date>`now() - make_interval(hours => ${window})`;

	const [jobDurRes, gensRes, completedRes, workersRes, spendRes, p95Res] = await Promise.all([
		// p95 job duration (wall-clock) over jobs completed in last 7d
		db
			.selectFrom('jobs')
			.select(sql<number>`percentile_cont(0.95) within group (order by duration)`.as('p95'))
			.where('status', '=', 'completed')
			.where('completed_at', '>=', stat_window)
			.where('duration', 'is not', null)
			.executeTakeFirst(),

		// Count of Generations
		db
			.selectFrom('generated_content')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('created_at', '>=', stat_window)
			.executeTakeFirstOrThrow(),

		// Count of Completed jobs
		db
			.selectFrom('jobs')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('status', '=', 'completed')
			.where('completed_at', '>=', stat_window)
			.executeTakeFirstOrThrow(),

		// Workers online (distinct worker_ids with in_progress jobs)
		db
			.selectFrom('jobs')
			.select(sql<number>`count(distinct worker_id)::int`.as('count'))
			.where('status', '=', 'in_progress')
			.where('worker_id', 'is not', null)
			.executeTakeFirstOrThrow(),

		// Estimated LLM spend
		db
			.selectFrom('generated_content')
			.leftJoin('model_configs', 'model_configs.id', 'generated_content.model_config_id')
			.select([
				'model_configs.model',
				'generated_content.input_tokens',
				'generated_content.output_tokens',
				'generated_content.total_duration'
			])
			.where('generated_content.created_at', '>=', stat_window)
			.execute(),

		// p95 llm latency
		db
			.selectFrom('generated_content')
			.select(sql<number>`percentile_cont(0.95) within group (order by total_duration)`.as('p95'))
			.where('created_at', '>=', stat_window)
			.where('total_duration', 'is not', null)
			.executeTakeFirst()
	]);

	let totalSpend = 0;
	for (const row of spendRes) {
		totalSpend += generationCost(
			row.model ?? null,
			row.input_tokens,
			row.output_tokens,
			row.total_duration
		);
	}
	const genCount = gensRes.count;
	const avgCost = genCount > 0 ? totalSpend / genCount : 0;

	return {
		p95JobDuration: jobDurRes?.p95 != null ? Math.round(jobDurRes.p95 * 10) / 10 : null,
		generationsCount: genCount,
		completedCount: completedRes.count,
		workersOnline: workersRes.count,
		totalWorkerSlots: 8,
		llmSpend: Math.round(totalSpend * 100) / 100,
		avgCostPerGen: Math.round(avgCost * 1000) / 1000,
		p95Latency: p95Res?.p95 != null ? Math.round(p95Res.p95 * 10) / 10 : null
	};
}

export async function getFilingIngestionByDay(days: number): Promise<IngestionDayRow[]> {
	const rows = await db
		.selectFrom('filings')
		.select([
			sql<string>`to_char(date_trunc('day', filing_date), 'MM/DD')`.as('label'),
			sql<number>`count(*) filter (where form like '10-K%')::int`.as('k'),
			sql<number>`count(*) filter (where form like '10-Q%')::int`.as('q'),
			sql<number>`count(*) filter (where form like '8-K%')::int`.as('_8k'),
			sql<number>`count(*) filter (where form not like '10-K%' and form not like '10-Q%' and form not like '8-K%')::int`.as(
				'other'
			)
		])
		.where('filing_date', '>=', sql`now() - ${sql.lit(days + ' days')}::interval`)
		.groupBy(sql`date_trunc('day', filing_date)`)
		.orderBy(sql`date_trunc('day', filing_date)`)
		.execute();

	return rows;
}

export async function getRecentFilings(limit: number): Promise<RecentFilingRow[]> {
	const rows = await db
		.selectFrom('filings')
		.innerJoin('companies', 'companies.id', 'filings.company_id')
		.leftJoin('documents', 'documents.filing_id', 'filings.id')
		.select([
			sql<string>`to_char(filings.filing_date, 'HH24:MI:SS')`.as('time'),
			'companies.cik',
			'companies.name as company',
			'filings.form',
			sql<number>`count(documents.id)::int`.as('doc_count')
		])
		.groupBy([
			'filings.id',
			'filings.filing_date',
			'companies.cik',
			'companies.name',
			'filings.form'
		])
		.orderBy('filings.filing_date', 'desc')
		.limit(limit)
		.execute();

	return rows.map((r) => ({
		time: r.time,
		cik: r.cik,
		company: r.company,
		form: r.form,
		docCount: r.doc_count,
		status: r.doc_count > 0 ? ('indexed' as const) : ('parsed' as const)
	}));
}

export async function getContentBreakdown(): Promise<ContentBreakdownRow[]> {
	const ago24h = sql`now() - interval '24 hours'`;

	const rows = await db
		.selectFrom('generated_content')
		.leftJoin('model_configs', 'model_configs.id', 'generated_content.model_config_id')
		.select([
			'generated_content.content_stage',
			'generated_content.document_type',
			sql<number>`count(*)::int`.as('count'),
			sql<number>`avg(generated_content.total_duration)`.as('avg_dur'),
			'model_configs.model'
		])
		.where('generated_content.created_at', '>=', ago24h)
		.groupBy([
			'generated_content.content_stage',
			'generated_content.document_type',
			'model_configs.model'
		])
		.execute();

	// Aggregate by content label
	const map = new Map<
		string,
		{ count: number; totalDur: number; durCount: number; totalCost: number }
	>();

	for (const r of rows) {
		const label = contentLabel(r.content_stage, r.document_type);
		const existing = map.get(label) ?? { count: 0, totalDur: 0, durCount: 0, totalCost: 0 };
		existing.count += r.count;
		if (r.avg_dur != null) {
			existing.totalDur += r.avg_dur * r.count;
			existing.durCount += r.count;
		}
		map.set(label, existing);
	}

	// Compute per-row costs from a separate query (needed because grouping includes model)
	const costRows = await db
		.selectFrom('generated_content')
		.leftJoin('model_configs', 'model_configs.id', 'generated_content.model_config_id')
		.select([
			'generated_content.content_stage',
			'generated_content.document_type',
			'model_configs.model',
			'generated_content.input_tokens',
			'generated_content.output_tokens',
			'generated_content.total_duration'
		])
		.where('generated_content.created_at', '>=', ago24h)
		.execute();

	for (const r of costRows) {
		const label = contentLabel(r.content_stage, r.document_type);
		const existing = map.get(label);
		if (existing) {
			existing.totalCost += generationCost(
				r.model ?? null,
				r.input_tokens,
				r.output_tokens,
				r.total_duration
			);
		}
	}

	const total = Array.from(map.values()).reduce((s, v) => s + v.count, 0);

	return Array.from(map.entries())
		.sort((a, b) => b[1].count - a[1].count)
		.map(([kind, v]) => ({
			kind,
			count: v.count,
			pct: total > 0 ? `${((v.count / total) * 100).toFixed(1)}%` : '0%',
			avgLatency: v.durCount > 0 ? `${(v.totalDur / v.durCount).toFixed(1)}s` : '—',
			totalCost: `$${v.totalCost.toFixed(2)}`
		}));
}

export async function getContentThroughput(days: number): Promise<ThroughputDayRow[]> {
	const rows = await db
		.selectFrom('generated_content')
		.select([
			sql<string>`to_char(date_trunc('day', created_at), 'MM/DD')`.as('label'),
			sql<number>`count(*)::int`.as('v')
		])
		.where('created_at', '>=', sql`now() - ${sql.lit(days + ' days')}::interval`)
		.groupBy(sql`date_trunc('day', created_at)`)
		.orderBy(sql`date_trunc('day', created_at)`)
		.execute();

	return rows;
}

export async function getContentLog(limit: number): Promise<ContentLogRow[]> {
	const rows = await db
		.selectFrom('generated_content')
		.leftJoin('model_configs', 'model_configs.id', 'generated_content.model_config_id')
		// Resolve the owning company through whichever link is set: filing/document
		// generations leave company_id null but carry filing_id or document_id, each
		// of which points back to a company.
		.leftJoin('filings as gc_filing', 'gc_filing.id', 'generated_content.filing_id')
		.leftJoin('documents as gc_doc', 'gc_doc.id', 'generated_content.document_id')
		.leftJoin('filings as doc_filing', 'doc_filing.id', 'gc_doc.filing_id')
		.leftJoin('companies as direct_co', 'direct_co.id', 'generated_content.company_id')
		.leftJoin('companies as filing_co', 'filing_co.id', 'gc_filing.company_id')
		.leftJoin('companies as doc_co', 'doc_co.id', 'gc_doc.company_id')
		.select([
			sql<string>`to_char(generated_content.created_at, 'HH24:MI:SS')`.as('time'),
			'generated_content.content_stage',
			'generated_content.document_type',
			'generated_content.form_type',
			'generated_content.content_hash',
			sql<string | null>`coalesce(direct_co.ticker, filing_co.ticker, doc_co.ticker)`.as('ticker'),
			sql<string | null>`coalesce(direct_co.name, filing_co.name, doc_co.name)`.as('company_name'),
			sql<string | null>`coalesce(gc_filing.form, doc_filing.form)`.as('filing_form'),
			sql<
				number | null
			>`extract(year from coalesce(gc_filing.period_of_report, doc_filing.period_of_report))::int`.as(
				'fiscal_year'
			),
			'model_configs.model',
			'generated_content.input_tokens',
			'generated_content.output_tokens',
			'generated_content.total_duration',
			'generated_content.warning'
		])
		.orderBy('generated_content.created_at', 'desc')
		.limit(limit)
		.execute();

	return rows.map((r) => {
		const kind = contentLabel(r.content_stage, r.document_type);
		const company = r.ticker ?? r.company_name ?? '—';

		// Prefer structured filing context (form · fiscal year · section) over the
		// internal `description` key, which is opaque (e.g. "controls_procedures_single_summary").
		const form = r.form_type ?? r.filing_form ?? null;
		const fy = r.fiscal_year ? `FY${r.fiscal_year}` : null;
		const section = sectionLabel(r.document_type);
		const context = [form, fy, section].filter(Boolean).join(' · ') || '—';

		// Deep-link to the content page (/g/[ticker]/[sha], matched by hash prefix).
		// Needs a real ticker, so company-less content (e.g. groups) isn't linkable.
		const href =
			r.ticker && r.content_hash ? `/g/${r.ticker}/${r.content_hash.slice(0, 12)}` : null;

		const cost = generationCost(r.model ?? null, r.input_tokens, r.output_tokens, r.total_duration);

		let status: 'ok' | 'retry' | 'fail' = 'ok';
		if (r.warning) {
			status = r.warning.toLowerCase().includes('fail') ? 'fail' : 'retry';
		}

		return {
			time: r.time,
			kind,
			company,
			context,
			href,
			model: r.model ?? '—',
			tokensIn: r.input_tokens ?? 0,
			tokensOut: r.output_tokens ?? 0,
			latency: r.total_duration != null ? `${r.total_duration.toFixed(1)}s` : '—',
			cost: `$${cost.toFixed(2)}`,
			status
		};
	});
}

export async function getJobQueueStats(): Promise<JobQueueStats> {
	const ago24h = sql`now() - interval '24 hours'`;

	const [runningRes, queuedRes, backoffRes, failedRes] = await Promise.all([
		db
			.selectFrom('jobs')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('status', '=', 'in_progress')
			.executeTakeFirstOrThrow(),

		db
			.selectFrom('jobs')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('status', '=', 'pending')
			.executeTakeFirstOrThrow(),

		db
			.selectFrom('jobs')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('status', '=', 'backoff')
			.executeTakeFirstOrThrow(),

		db
			.selectFrom('jobs')
			.select(sql<number>`count(*)::int`.as('count'))
			.where('status', '=', 'failed')
			.where('completed_at', '>=', ago24h)
			.executeTakeFirstOrThrow()
	]);

	return {
		running: runningRes.count,
		queued: queuedRes.count,
		backoff: backoffRes.count,
		failed24h: failedRes.count
	};
}

export async function getJobQueueDepth(hours: number): Promise<QueueDepthPoint[]> {
	// Approximate queue depth: for each hourly bucket, count jobs created before that time
	// that were not yet completed (or were completed after that time)
	const rows = await sql<{ label: string; v: number }>`
		with buckets as (
			select generate_series(
				date_trunc('hour', now() - ${sql.lit(hours + ' hours')}::interval),
				date_trunc('hour', now()),
				'1 hour'::interval
			) as bucket_time
		)
		select
			to_char(b.bucket_time, 'HH24:MI') as label,
			count(j.id)::int as v
		from buckets b
		left join jobs j on
			j.created_at <= b.bucket_time
			and (j.completed_at is null or j.completed_at > b.bucket_time)
			and j.status in ('pending', 'backoff', 'in_progress', 'failed', 'cancelled')
		group by b.bucket_time
		order by b.bucket_time
	`.execute(db);

	return rows.rows;
}

export async function getActiveJobs(limit: number): Promise<ActiveJobRow[]> {
	const rows = await db
		.selectFrom('jobs')
		.select([
			'id',
			'job_type',
			'priority',
			'params',
			'retry_count',
			'max_retries',
			'worker_id',
			'status',
			'created_at',
			'started_at'
		])
		.where('status', 'in', ['pending', 'backoff', 'in_progress'])
		.orderBy(sql`case when status = 'in_progress' then 0 else 1 end`)
		.orderBy('priority', 'desc')
		.orderBy('created_at', 'asc')
		.limit(limit)
		.execute();

	return rows.map((r) => {
		const params = r.params as Record<string, unknown> | null;
		const { company, detail } = jobContext(r.job_type, params);

		// Runtime is measured from when the job actually started executing.
		// Queued jobs haven't started yet, so they have no runtime.
		const startedAt = r.started_at ? new Date(r.started_at as unknown as string).getTime() : null;
		let runtime = '—';
		if (startedAt != null) {
			const secs = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
			runtime =
				secs >= 3600
					? `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
					: secs >= 60
						? `${Math.floor(secs / 60)}m ${secs % 60}s`
						: `${secs}s`;
		}

		let state: 'running' | 'queued' | 'backoff' = 'queued';
		if (r.status === 'in_progress') state = 'running';
		else if (r.status === 'backoff') state = 'backoff';

		return {
			id: r.id,
			shortId: r.id.slice(0, 10),
			kind: jobKindLabel(r.job_type),
			priority: r.priority,
			company,
			target: detail,
			attempt: `${r.retry_count + 1}/${r.max_retries}`,
			workerId: r.worker_id ?? '—',
			state,
			runtime
		};
	});
}

export async function getWorkerSummary(): Promise<WorkerRow[]> {
	// Get currently active workers from in-progress jobs
	const activeRows = await db
		.selectFrom('jobs')
		.select(['worker_id', 'job_type', 'params', 'started_at'])
		.where('status', '=', 'in_progress')
		.where('worker_id', 'is not', null)
		.execute();

	// Get throughput per worker (completed in last hour)
	const throughputRows = await db
		.selectFrom('jobs')
		.select(['worker_id', sql<number>`count(*)::int`.as('completed_count')])
		.where('status', '=', 'completed')
		.where('completed_at', '>=', sql`now() - interval '1 hour'`)
		.where('worker_id', 'is not', null)
		.groupBy('worker_id')
		.execute();

	const throughputMap = new Map<string, number>();
	for (const r of throughputRows) {
		if (r.worker_id) throughputMap.set(r.worker_id, r.completed_count);
	}

	// Collect all known worker_ids (active + recently active)
	const workerIds = new Set<string>();
	for (const r of activeRows) if (r.worker_id) workerIds.add(r.worker_id);
	for (const r of throughputRows) if (r.worker_id) workerIds.add(r.worker_id);

	const activeMap = new Map<string, (typeof activeRows)[0]>();
	for (const r of activeRows) {
		if (r.worker_id) activeMap.set(r.worker_id, r);
	}

	return Array.from(workerIds)
		.sort()
		.map((wid) => {
			const active = activeMap.get(wid);
			const params = active?.params as Record<string, unknown> | null;
			let jobDesc = '—';
			if (active) {
				// e.g. "Filing content · AMZN · 10-K · FY2025" — same kind/company/detail
				// the in-flight table shows, flattened into one line for the card.
				const { company, detail } = jobContext(active.job_type, params);
				jobDesc = [
					jobKindLabel(active.job_type),
					company !== '—' ? company : null,
					detail !== '—' ? detail : null
				]
					.filter(Boolean)
					.join(' · ');
			}

			let elapsed = '—';
			if (active?.started_at) {
				const secs = Math.floor(
					(Date.now() - new Date(active.started_at as unknown as string).getTime()) / 1000
				);
				const m = Math.floor(secs / 60);
				const s = secs % 60;
				elapsed = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
			}

			const rate = throughputMap.get(wid) ?? 0;

			return {
				id: wid,
				status: active ? ('running' as const) : ('idle' as const),
				job: jobDesc,
				elapsed,
				rate: `${rate} / hr`
			};
		});
}

// ── Consolidated snapshot ──
//
// The default time window (in days for throughput, hours for queue depth) used
// across the status dashboard's windowed stats. Shared by the SSR `load` and
// the `/api/status` polling endpoint so both render the same scope.
export const STAT_WINDOW = 6;

export interface StatusSnapshot {
	hero: HeroStats;
	ingestionDays: IngestionDayRow[];
	recentFilings: RecentFilingRow[];
	contentBreakdown: ContentBreakdownRow[];
	contentThroughput: ThroughputDayRow[];
	contentLog: ContentLogRow[];
	queueStats: JobQueueStats;
	queueDepth: QueueDepthPoint[];
	activeJobs: ActiveJobRow[];
	workers: WorkerRow[];
}

// Single source of truth for the status dashboard payload. Both the page's
// server `load` (initial SSR) and `GET /api/status` (60s poll) call this with
// the same window, so the two never drift.
export async function collectStatus(window: number = STAT_WINDOW): Promise<StatusSnapshot> {
	const [
		hero,
		ingestionDays,
		recentFilings,
		contentBreakdown,
		contentThroughput,
		contentLog,
		queueStats,
		queueDepth,
		activeJobs,
		workers
	] = await Promise.all([
		getHeroStats(window),
		getFilingIngestionByDay(14),
		getRecentFilings(8),
		getContentBreakdown(),
		getContentThroughput(window),
		getContentLog(9),
		getJobQueueStats(),
		getJobQueueDepth(window),
		getActiveJobs(10),
		getWorkerSummary()
	]);

	return {
		hero,
		ingestionDays,
		recentFilings,
		contentBreakdown,
		contentThroughput,
		contentLog,
		queueStats,
		queueDepth,
		activeJobs,
		workers
	};
}
