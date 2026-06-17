// Display helpers for the job queue, mirroring the server CLI (symbology/cli/jobs.py
// + cli/shortid.py) so the status dashboard and `jobs list` read the same.

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The display short id for a UUID: its last segment (the random uuid7 tail). */
export const shortId = (value: string): string => String(value).split('-').at(-1) ?? String(value);

/** shortId(value) if it's a UUID, else the value unchanged (for mixed fields). */
export const maybeShortId = (value: unknown): string => {
	const s = String(value);
	return UUID_RE.test(s) ? shortId(s) : s;
};

/**
 * Curate a job's heterogeneous params into the compact context string the CLI
 * shows — UUID-valued fields (filing_id, diff_set_id, the filing_diff from→to
 * pair) shortened; tickers / accession numbers / forms left intact.
 */
export function formatJobContext(jobType: string, params: Record<string, unknown> | null): string {
	const p = params ?? {};
	const has = (k: string) =>
		p[k] != null && p[k] !== '' && !(Array.isArray(p[k]) && (p[k] as unknown[]).length === 0);
	const pick = (...keys: string[]) => keys.filter(has).map((k) => `${k}=${maybeShortId(p[k])}`);

	let parts: string[] = [];
	switch (jobType) {
		case 'company_ingestion':
			parts = pick('ticker');
			break;
		case 'filing_ingestion':
			parts = pick('ticker', 'form', 'count');
			break;
		case 'filing_page_content':
			parts = pick('ticker', 'form', 'year');
			break;
		case 'company_page_content':
			parts = pick('ticker', 'form', 'lookback');
			break;
		case 'embed_filing':
			parts = pick('filing_id', 'accession_number');
			break;
		case 'filing_diff': {
			const left = p['from'] ?? p['left_filing_id'];
			const right = p['to'] ?? p['right_filing_id'];
			if (left && right) parts.push(`${maybeShortId(left)} -> ${maybeShortId(right)}`);
			parts.push(...pick('form'));
			break;
		}
		case 'diff_summary':
			parts = pick('diff_set_id', 'form');
			break;
		case 'content_generation':
			parts = pick('company_ticker', 'form_type', 'document_type', 'content_stage', 'description');
			break;
		case 'company_group_pipeline': {
			const tickers = p['tickers'];
			if (Array.isArray(tickers) && tickers.length) parts.push(`tickers=${tickers.join(',')}`);
			parts.push(...pick('group_slug'));
			break;
		}
		case 'bulk_ingest': {
			const filings = p['filings'];
			parts = [`${Array.isArray(filings) ? filings.length : 0} filings`];
			break;
		}
		case 'test':
			parts = pick('sleep');
			break;
	}

	if (parts.length === 0) {
		// Fallback: the first few scalar params for an unhandled type.
		parts = Object.entries(p)
			.filter(([, v]) => ['string', 'number', 'boolean'].includes(typeof v))
			.slice(0, 3)
			.map(([k, v]) => `${k}=${maybeShortId(v)}`);
	}
	return parts.join(', ');
}

/** A compact relative time: '3h ago', 'in 2m', 'now'. Empty input → '-'. */
export function relativeTime(value: string | null | undefined): string {
	if (!value) return '-';
	const then = new Date(value).getTime();
	if (Number.isNaN(then)) return '-';
	let secs = (Date.now() - then) / 1000;
	const future = secs < 0;
	secs = Math.abs(secs);
	let val: string;
	if (secs >= 86400) val = `${Math.floor(secs / 86400)}d`;
	else if (secs >= 3600) val = `${Math.floor(secs / 3600)}h`;
	else if (secs >= 60) val = `${Math.floor(secs / 60)}m`;
	else val = `${Math.floor(secs)}s`;
	return future ? `in ${val}` : `${val} ago`;
}

export interface JobTimestamps {
	createdAt?: string | null;
	startedAt?: string | null;
	scheduledAt?: string | null;
	completedAt?: string | null;
	updatedAt?: string | null;
}

/**
 * One status-aware relative timestamp — the job's most recent / pending event —
 * mirroring the CLI's "When" column: 'done 3h ago' (completed), 'started 2m ago'
 * (running), 'retry in 1m' (backoff), 'queued 5m ago' (pending).
 */
export function formatJobWhen(status: string, ts: JobTimestamps): string {
	switch (status) {
		case 'completed':
			return `done ${relativeTime(ts.completedAt ?? ts.updatedAt)}`;
		case 'failed':
			return `failed ${relativeTime(ts.completedAt ?? ts.updatedAt)}`;
		case 'cancelled':
			return `cancelled ${relativeTime(ts.completedAt ?? ts.updatedAt)}`;
		case 'in_progress':
			return `started ${relativeTime(ts.startedAt)}`;
		case 'backoff':
			return `retry ${relativeTime(ts.scheduledAt)}`;
		default:
			return `queued ${relativeTime(ts.createdAt)}`;
	}
}
