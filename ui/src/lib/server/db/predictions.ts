import { db } from '../db';

/**
 * Read-time prediction of upcoming periodic filings (10-K / 10-Q) for a set of
 * companies. There is no stored schedule — the SEC doesn't publish one — so we
 * estimate from each company's own history: filing lag (filing_date −
 * period_of_report) is near-constant per company, and period ends advance one
 * quarter at a time. Fiscal years are 52/53-week so period ends drift a few days
 * year-over-year; these are estimates, surfaced as "est. <date>".
 *
 * Pure computation: no new tables, no migration. The Python services don't use
 * this; it's UI-side for the watchlist calendar.
 */

const MS_PER_DAY = 86_400_000;

/** Fallback lags (days from period end to filing) when a company has too few
 *  samples of a form. 10-K annual reports file slower than 10-Q quarterlies. */
const DEFAULT_LAG: Record<string, number> = { '10-K': 75, '10-Q': 40 };

/** A prediction we keep showing once filed-late/overdue, until this stale. Past
 *  this we assume our data is behind and roll forward to the next period. */
const OVERDUE_GRACE_DAYS = 21;

export interface UpcomingFiling {
	companyId: string;
	ticker: string;
	companyName: string;
	form: '10-K' | '10-Q';
	/** ISO date — the predicted next period end (period_of_report). */
	periodOfReport: string;
	/** ISO date — predicted filing date (period end + median lag). */
	predictedFilingDate: string;
	/** Human label, e.g. "Q1 FY26" (10-Q) or "FY25" (10-K). */
	periodLabel: string;
	/** Days from `today` to the predicted filing; negative = overdue. */
	daysUntil: number;
	overdue: boolean;
	confidence: 'high' | 'low';
	basis: { sampleSize: number; medianLagDays: number };
}

// ── Date helpers (all arithmetic in UTC to avoid TZ day-shifts) ──

/** Parse a date-only or timestamp value to a UTC midnight Date. */
function toUtcDate(val: unknown): Date {
	const s = val instanceof Date ? val.toISOString() : String(val);
	const [y, m, d] = s.split('T')[0].split('-').map(Number);
	return new Date(Date.UTC(y, m - 1, d));
}

function toIsoDate(d: Date): string {
	return d.toISOString().split('T')[0];
}

function lastDayOfUtcMonth(year: number, monthIndex: number): number {
	return new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
}

/** Add whole months, clamping the day to the target month's last day (so a
 *  month-end period like 03-31 maps to 06-30, not an overflow into July). */
function addMonthsClamped(d: Date, months: number): Date {
	const y = d.getUTCFullYear();
	const m = d.getUTCMonth() + months;
	const targetYear = y + Math.floor(m / 12);
	const targetMonth = ((m % 12) + 12) % 12;
	const day = Math.min(d.getUTCDate(), lastDayOfUtcMonth(targetYear, targetMonth));
	return new Date(Date.UTC(targetYear, targetMonth, day));
}

function addDays(d: Date, days: number): Date {
	return new Date(d.getTime() + days * MS_PER_DAY);
}

function diffDays(a: Date, b: Date): number {
	return Math.round((a.getTime() - b.getTime()) / MS_PER_DAY);
}

function median(nums: number[]): number {
	if (nums.length === 0) return 0;
	const sorted = [...nums].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

interface FilingRow {
	company_id: string;
	form: string;
	filing_date: unknown;
	period_of_report: unknown;
	ticker: string;
	name: string;
	display_name: string | null;
	fiscal_year_end: unknown;
}

interface Group {
	companyId: string;
	ticker: string;
	companyName: string;
	fye: Date | null; // the company's fiscal_year_end date (month/day used)
	rows: { form: string; filed: Date; period: Date }[]; // sorted by period asc
}

/** Median filing lag for one form within a group (last ≤8 samples). Falls back
 *  to a per-form default when there are <2 samples. */
function lagFor(group: Group, form: string): { lag: number; samples: number } {
	const lags = group.rows
		.filter((r) => r.form === form)
		.slice(-8)
		.map((r) => diffDays(r.filed, r.period));
	if (lags.length < 2) return { lag: DEFAULT_LAG[form] ?? 45, samples: lags.length };
	return { lag: Math.round(median(lags)), samples: lags.length };
}

/** Quarter/year label for a predicted period end given the fiscal-year-end month. */
function periodLabel(form: '10-K' | '10-Q', period: Date, fyeMonth: number): string {
	const month = period.getUTCMonth() + 1;
	const year = period.getUTCFullYear();
	if (form === '10-K') {
		return `FY${String(year % 100).padStart(2, '0')}`;
	}
	// Quarters end ~3/6/9 months after the fiscal-year start (i.e. after FYE).
	const monthsAfterFye = (((month - fyeMonth) % 12) + 12) % 12;
	const q = Math.max(1, Math.min(3, Math.round(monthsAfterFye / 3)));
	// The fiscal year a quarter belongs to is the one whose FYE follows it.
	const fyYear = month > fyeMonth ? year + 1 : year;
	return `Q${q} FY${String(fyYear % 100).padStart(2, '0')}`;
}

/**
 * Predicted next periodic filings for the given companies, sorted by predicted
 * filing date. When `withinDays` is set, only filings due within that many days
 * ahead are returned (recently-overdue ones, within OVERDUE_GRACE_DAYS, are kept
 * so an expected-but-unfiled report still surfaces). `today` is injectable for
 * tests. Empty input → empty output.
 */
export async function getUpcomingFilings(
	companyIds: string[],
	opts: { withinDays?: number; today?: Date } = {}
): Promise<UpcomingFiling[]> {
	if (companyIds.length === 0) return [];
	const today = opts.today ?? new Date();

	const rows = (await db
		.selectFrom('filings as f')
		.innerJoin('companies as c', 'c.id', 'f.company_id')
		.select([
			'f.company_id',
			'f.form',
			'f.filing_date',
			'f.period_of_report',
			'c.ticker',
			'c.name',
			'c.display_name',
			'c.fiscal_year_end'
		])
		.where('f.company_id', 'in', companyIds)
		.where('f.form', 'in', ['10-K', '10-Q'])
		.where('f.period_of_report', 'is not', null)
		.orderBy('f.company_id')
		.orderBy('f.period_of_report', 'asc')
		.execute()) as FilingRow[];

	// Group by company; rows arrive period-ascending.
	const groups = new Map<string, Group>();
	for (const r of rows) {
		let g = groups.get(r.company_id);
		if (!g) {
			g = {
				companyId: r.company_id,
				ticker: r.ticker,
				companyName: r.display_name ?? r.name,
				fye: r.fiscal_year_end ? toUtcDate(r.fiscal_year_end) : null,
				rows: []
			};
			groups.set(r.company_id, g);
		}
		g.rows.push({
			form: r.form,
			filed: toUtcDate(r.filing_date),
			period: toUtcDate(r.period_of_report)
		});
	}

	const out: UpcomingFiling[] = [];
	for (const g of groups.values()) {
		if (g.rows.length === 0) continue;
		const latestPeriod = g.rows[g.rows.length - 1].period;
		// FYE month: prefer the company field; else the latest 10-K's month; else
		// the latest period's month.
		const latest10K = [...g.rows].reverse().find((r) => r.form === '10-K');
		const fyeMonth =
			(g.fye ? g.fye.getUTCMonth() + 1 : null) ??
			(latest10K ? latest10K.period.getUTCMonth() + 1 : null) ??
			latestPeriod.getUTCMonth() + 1;

		// Walk forward a quarter at a time until the predicted filing isn't badly
		// stale (data behind) — capped so a gap in history can't loop forever.
		let period = latestPeriod;
		let chosen: {
			form: '10-K' | '10-Q';
			period: Date;
			filed: Date;
			lag: number;
			samples: number;
		} | null = null;
		for (let i = 0; i < 6; i++) {
			let candidate = addMonthsClamped(period, 3);
			const month = candidate.getUTCMonth() + 1;
			// The quarter ending in (or adjacent to) the FYE month is the annual one.
			const monthsToFye = Math.min(
				(((month - fyeMonth) % 12) + 12) % 12,
				(((fyeMonth - month) % 12) + 12) % 12
			);
			const form: '10-K' | '10-Q' = monthsToFye <= 1 ? '10-K' : '10-Q';
			// For the annual report the period end *is* the fiscal year end, which we
			// know precisely — snap to it (month/day in the candidate's year). This
			// corrects retail 4-4-5 calendars where the Q3→FY gap isn't a clean
			// quarter. Quarterly period ends we can only estimate as +3 months.
			if (form === '10-K' && g.fye) {
				const day = Math.min(
					g.fye.getUTCDate(),
					lastDayOfUtcMonth(candidate.getUTCFullYear(), fyeMonth - 1)
				);
				candidate = new Date(Date.UTC(candidate.getUTCFullYear(), fyeMonth - 1, day));
			}
			period = candidate;
			const { lag, samples } = lagFor(g, form);
			const filed = addDays(candidate, lag);
			chosen = { form, period: candidate, filed, lag, samples };
			if (diffDays(filed, today) >= -OVERDUE_GRACE_DAYS) break;
		}
		if (!chosen) continue;

		const daysUntil = diffDays(chosen.filed, today);
		const lagRange = (() => {
			const ls = g.rows
				.filter((r) => r.form === chosen.form)
				.slice(-8)
				.map((r) => diffDays(r.filed, r.period));
			return ls.length ? Math.max(...ls) - Math.min(...ls) : 0;
		})();
		out.push({
			companyId: g.companyId,
			ticker: g.ticker,
			companyName: g.companyName,
			form: chosen.form,
			periodOfReport: toIsoDate(chosen.period),
			predictedFilingDate: toIsoDate(chosen.filed),
			periodLabel: periodLabel(chosen.form, chosen.period, fyeMonth),
			daysUntil,
			overdue: daysUntil < 0,
			confidence: chosen.samples >= 3 && lagRange <= 30 ? 'high' : 'low',
			basis: { sampleSize: chosen.samples, medianLagDays: chosen.lag }
		});
	}

	out.sort((a, b) => a.predictedFilingDate.localeCompare(b.predictedFilingDate));

	if (opts.withinDays != null) {
		return out.filter((u) => u.daysUntil <= opts.withinDays! && u.daysUntil >= -OVERDUE_GRACE_DAYS);
	}
	return out;
}
