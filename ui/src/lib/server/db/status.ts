import { db } from '../db';
import { sql } from 'kysely';
import { formatJobContext, formatJobWhen, shortId } from '$lib/utils/jobs';

/** DB timestamps are naive UTC; normalise to an ISO string with an explicit Z so
 *  relative-time math is correct regardless of the server's local timezone. */
function toIso(val: unknown): string | null {
	if (!val) return null;
	if (val instanceof Date) return val.toISOString();
	const s = String(val).replace(' ', 'T');
	return /[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`;
}

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
	failedCount: number;
	/** Share of finished jobs (completed + failed) in the window that failed, 0–1. */
	failureRate: number;
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
	// Index signature so rows satisfy StackedColumns' `Record<string, unknown>[]` prop.
	[key: string]: string | number;
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

export interface ModelBreakdownRow {
	model: string;
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
	shortId: string;
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
	/** Dead-lettered (retries exhausted) jobs within the stat window. */
	failedInWindow: number;
}

export interface QueueDepthPoint {
	label: string;
	v: number;
}

export interface WorkerRow {
	id: string;
	status: 'running' | 'idle';
	job: string;
	/** Raw job_type of the worker's current job, mirroring the jobs list. */
	type: string;
	/** Curated params context for the current job, mirroring the jobs list. */
	context: string;
	elapsed: string;
	rate: string;
}

// The job statuses the recent-jobs table can be filtered by. Mirrors the
// server's JobStatus enum; used to validate the `status` query param before it
// reaches a query.
export const JOB_STATUS_FILTERS = [
	'pending',
	'in_progress',
	'backoff',
	'completed',
	'failed',
	'cancelled'
] as const;
export type JobStatusFilter = (typeof JOB_STATUS_FILTERS)[number];

/** Narrow an arbitrary string to a valid job-status filter, or null. */
export function parseJobStatusFilter(value: string | null | undefined): JobStatusFilter | null {
	return value && (JOB_STATUS_FILTERS as readonly string[]).includes(value)
		? (value as JobStatusFilter)
		: null;
}

// ── Queries ──

export async function getHeroStats(window: number): Promise<HeroStats> {
	const stat_window = sql<Date>`now() - make_interval(hours => ${window})`;

	const [jobDurRes, gensRes, completedRes, failedRes, workersRes, spendRes, p95Res] =
		await Promise.all([
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

			// Count of failed jobs (dead-lettered) in the same window — drives the
			// hero header's failure-rate health state.
			db
				.selectFrom('jobs')
				.select(sql<number>`count(*)::int`.as('count'))
				.where('status', '=', 'failed')
				.where('completed_at', '>=', stat_window)
				.executeTakeFirstOrThrow(),

			// Workers online: live (idle/running) rows in the first-class workers
			// table whose heartbeat is still fresh. `total` counts every worker that
			// isn't dead (i.e. recently seen) for the online/registered ratio.
			db
				.selectFrom('workers')
				.select([
					sql<number>`count(*) filter (where status in ('idle','running') and last_heartbeat >= now() - make_interval(secs => ${WORKER_HEARTBEAT_STALE_SECONDS}))::int`.as(
						'online'
					),
					sql<number>`count(*) filter (where status <> 'dead')::int`.as('total')
				])
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

	const completedCount = completedRes.count;
	const failedCount = failedRes.count;
	const finished = completedCount + failedCount;
	const failureRate = finished > 0 ? failedCount / finished : 0;

	return {
		p95JobDuration: jobDurRes?.p95 != null ? Math.round(jobDurRes.p95 * 10) / 10 : null,
		generationsCount: genCount,
		completedCount,
		failedCount,
		failureRate,
		workersOnline: workersRes.online,
		totalWorkerSlots: workersRes.total,
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
		.where('filing_date', '>=', sql<Date>`now() - ${sql.lit(days + ' days')}::interval`)
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
	const ago24h = sql<Date>`now() - interval '24 hours'`;

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

export async function getModelBreakdown(): Promise<ModelBreakdownRow[]> {
	const ago24h = sql<Date>`now() - interval '24 hours'`;

	const rows = await db
		.selectFrom('generated_content')
		.leftJoin('model_configs', 'model_configs.id', 'generated_content.model_config_id')
		.select([
			'model_configs.model',
			'generated_content.input_tokens',
			'generated_content.output_tokens',
			'generated_content.total_duration'
		])
		.where('generated_content.created_at', '>=', ago24h)
		.execute();

	// Aggregate by model name. Cost mixes per-token (Claude) and per-second
	// (self-hosted) rates, so it can't be a single SQL sum — meter each row.
	const map = new Map<
		string,
		{ count: number; totalDur: number; durCount: number; totalCost: number }
	>();

	for (const r of rows) {
		const model = r.model ?? 'Unknown';
		const existing = map.get(model) ?? { count: 0, totalDur: 0, durCount: 0, totalCost: 0 };
		existing.count += 1;
		if (r.total_duration != null) {
			existing.totalDur += r.total_duration;
			existing.durCount += 1;
		}
		existing.totalCost += generationCost(
			r.model ?? null,
			r.input_tokens,
			r.output_tokens,
			r.total_duration
		);
		map.set(model, existing);
	}

	const total = Array.from(map.values()).reduce((s, v) => s + v.count, 0);

	return Array.from(map.entries())
		.sort((a, b) => b[1].count - a[1].count)
		.map(([model, v]) => ({
			model,
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
		.where('created_at', '>=', sql<Date>`now() - ${sql.lit(days + ' days')}::interval`)
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
			'generated_content.id',
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

		// Deep-link to the synthesis page (/s/[sha], matched by hash prefix). The
		// hash alone identifies any content, so company-less rows (e.g. groups) link too.
		const href = r.content_hash ? `/s/${r.content_hash.slice(0, 12)}` : null;

		const cost = generationCost(r.model ?? null, r.input_tokens, r.output_tokens, r.total_duration);

		let status: 'ok' | 'retry' | 'fail' = 'ok';
		if (r.warning) {
			status = r.warning.toLowerCase().includes('fail') ? 'fail' : 'retry';
		}

		return {
			time: r.time,
			shortId: shortId(r.id),
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

export async function getJobQueueStats(window: number = STAT_WINDOW): Promise<JobQueueStats> {
	// running / queued / backoff are point-in-time queue depths (no window); only
	// the failed (dead-letter) count is windowed, scoped to the same stat window
	// as the rest of the dashboard so the "Failed" stat matches its label.
	const windowStart = sql<Date>`now() - make_interval(hours => ${window})`;

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
			.where('completed_at', '>=', windowStart)
			.executeTakeFirstOrThrow()
	]);

	return {
		running: runningRes.count,
		queued: queuedRes.count,
		backoff: backoffRes.count,
		failedInWindow: failedRes.count
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

export interface RecentJobRow {
	id: string;
	shortId: string;
	type: string; // raw job_type, mirroring `jobs list`
	context: string;
	status: string;
	priority: number;
	attempt: string;
	worker: string;
	when: string;
}

/**
 * Recent jobs (newest first), shaped to mirror the CLI's `jobs list`: short id,
 * raw type, curated context, status, priority, attempt, worker, and a single
 * status-aware "When". Powers the scrollable status table.
 *
 * With no `status`, returns the last `limit` jobs across all statuses (the
 * default dashboard view). With a `status`, the query is scoped to that status
 * first, so e.g. failed jobs surface even when they sit far beyond the most
 * recent `limit` rows — the queue can be deep with pending work while the
 * failures the operator cares about are older.
 */
export async function getRecentJobs(
	limit: number,
	status: JobStatusFilter | null = null
): Promise<RecentJobRow[]> {
	let query = db
		.selectFrom('jobs')
		.select([
			'id',
			'job_type',
			'params',
			'status',
			'priority',
			'retry_count',
			'max_retries',
			'worker_id',
			'created_at',
			'started_at',
			'scheduled_at',
			'completed_at',
			'updated_at'
		])
		// Order by id, not created_at: uuid7 ids are time-ordered AND the primary
		// key, so this is an index scan (no full-table sort) yet still newest-first —
		// keeps the query cheap as the high-churn jobs table grows / polling speeds up.
		.orderBy('id', 'desc')
		.limit(limit);

	if (status) {
		query = query.where('status', '=', status);
	}

	const rows = await query.execute();

	return rows.map((r) => ({
		id: r.id,
		shortId: shortId(r.id),
		type: r.job_type,
		context: formatJobContext(r.job_type, r.params as Record<string, unknown> | null),
		status: r.status,
		priority: r.priority,
		attempt: `${r.retry_count + 1}/${r.max_retries}`,
		worker: r.worker_id ?? '-',
		when: formatJobWhen(r.status, {
			createdAt: toIso(r.created_at),
			startedAt: toIso(r.started_at),
			scheduledAt: toIso(r.scheduled_at),
			completedAt: toIso(r.completed_at),
			updatedAt: toIso(r.updated_at)
		})
	}));
}

// A worker self-heartbeats every ~15s (idle or running), so a live worker's
// last_heartbeat is always fresh. A crashed / SIGKILL'd worker stops beating;
// the reap sweep marks it dead and reclaims its job within ~stale_threshold, but
// until then we exclude it here by the same freshness cut so a dead worker
// doesn't linger on the dashboard. Matches worker_settings.stale_threshold (90s).
const WORKER_HEARTBEAT_STALE_SECONDS = 90;

export async function getWorkerSummary(): Promise<WorkerRow[]> {
	// Live workers straight from the registry, with their current job (if any)
	// joined in for the "what's it doing" line. A worker is shown if it's in a
	// live state with a fresh heartbeat — no more inferring presence from jobs.
	const workerRows = await db
		.selectFrom('workers')
		.leftJoin('jobs', 'jobs.id', 'workers.current_job_id')
		.select([
			'workers.id as id',
			'workers.status as status',
			'jobs.job_type as job_type',
			'jobs.params as params',
			'jobs.started_at as job_started_at'
		])
		.where('workers.status', 'in', ['idle', 'running'])
		.where(
			'workers.last_heartbeat',
			'>=',
			sql<Date>`now() - make_interval(secs => ${WORKER_HEARTBEAT_STALE_SECONDS})`
		)
		.orderBy('workers.id')
		.execute();

	// Throughput per worker (jobs completed in the last hour).
	const throughputRows = await db
		.selectFrom('jobs')
		.select(['worker_id', sql<number>`count(*)::int`.as('completed_count')])
		.where('status', '=', 'completed')
		.where('completed_at', '>=', sql<Date>`now() - interval '1 hour'`)
		.where('worker_id', 'is not', null)
		.groupBy('worker_id')
		.execute();

	const throughputMap = new Map<string, number>();
	for (const r of throughputRows) {
		if (r.worker_id) throughputMap.set(r.worker_id, r.completed_count);
	}

	return workerRows.map((w) => {
		const running = w.status === 'running' && w.job_type != null;

		let jobDesc = '—';
		// The raw type + curated params context, matching the recent-jobs table so
		// the two surfaces agree on what a worker is doing.
		let context = '—';
		if (w.job_type != null) {
			// e.g. "Filing content · AMZN · 10-K · FY2025" — same kind/company/detail
			// the in-flight table shows, flattened into one line for the card.
			const { company, detail } = jobContext(
				w.job_type,
				w.params as Record<string, unknown> | null
			);
			jobDesc = [
				jobKindLabel(w.job_type),
				company !== '—' ? company : null,
				detail !== '—' ? detail : null
			]
				.filter(Boolean)
				.join(' · ');
			context = formatJobContext(w.job_type, w.params as Record<string, unknown> | null) || '—';
		}

		let elapsed = '—';
		if (running && w.job_started_at) {
			const secs = Math.floor(
				(Date.now() - new Date(w.job_started_at as unknown as string).getTime()) / 1000
			);
			const m = Math.floor(secs / 60);
			const s = secs % 60;
			elapsed = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
		}

		const rate = throughputMap.get(w.id) ?? 0;

		return {
			id: w.id,
			status: running ? ('running' as const) : ('idle' as const),
			job: jobDesc,
			type: w.job_type ?? '—',
			context,
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

/** The fast-changing slice of the dashboard — polled more often than the full
 *  snapshot (its time-series/aggregate queries are heavier and slow-moving). */
export interface QueueSnapshot {
	queueStats: JobQueueStats;
	recentJobs: RecentJobRow[];
	workers: WorkerRow[];
}

export interface StatusSnapshot {
	hero: HeroStats;
	ingestionDays: IngestionDayRow[];
	recentFilings: RecentFilingRow[];
	contentBreakdown: ContentBreakdownRow[];
	modelBreakdown: ModelBreakdownRow[];
	contentThroughput: ThroughputDayRow[];
	contentLog: ContentLogRow[];
	queueStats: JobQueueStats;
	queueDepth: QueueDepthPoint[];
	recentJobs: RecentJobRow[];
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
		modelBreakdown,
		contentThroughput,
		contentLog,
		queueStats,
		queueDepth,
		recentJobs,
		workers
	] = await Promise.all([
		getHeroStats(window),
		getFilingIngestionByDay(14),
		getRecentFilings(8),
		getContentBreakdown(),
		getModelBreakdown(),
		getContentThroughput(window),
		getContentLog(125),
		getJobQueueStats(window),
		getJobQueueDepth(window),
		getRecentJobs(125),
		getWorkerSummary()
	]);

	return {
		hero,
		ingestionDays,
		recentFilings,
		contentBreakdown,
		modelBreakdown,
		contentThroughput,
		contentLog,
		queueStats,
		queueDepth,
		recentJobs,
		workers
	};
}

/**
 * The queue slice only (job counts, recent jobs, workers) — the cheap, fast-moving
 * queries the dashboard polls frequently, without re-running the heavy time-series
 * aggregations in :func:`collectStatus`.
 */
export async function collectQueueStatus(
	window: number = STAT_WINDOW,
	jobStatus: JobStatusFilter | null = null
): Promise<QueueSnapshot> {
	// A status filter is a deliberate lookup, not the live tail: widen the limit so
	// matches beyond the default 100-row window surface (e.g. failed jobs buried
	// under a deep pile of pending ones). The unfiltered view stays at 100.
	const limit = jobStatus ? 250 : 100;
	const [queueStats, recentJobs, workers] = await Promise.all([
		getJobQueueStats(window),
		getRecentJobs(limit, jobStatus),
		getWorkerSummary()
	]);
	return { queueStats, recentJobs, workers };
}
