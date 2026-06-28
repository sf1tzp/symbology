import { sql } from 'kysely';
import { db } from '../db';

export interface PrioritizeFilingInput {
	accession: string;
	ticker: string;
	form: string;
	/** Candidate fiscal years (period-of-report and/or filing-date years). */
	years: number[];
}

/**
 * Move a filing's queued analysis to the front of the worker queue — the
 * supporter "prioritize" perk. Sets `priority = 0` (JobPriority.DEP_UNBLOCK, the
 * highest band) on any PENDING analysis job for this filing.
 *
 * FILING_PAGE_CONTENT / COMPANY_PAGE_CONTENT jobs are keyed either by
 * `accession_number` or by `ticker` + `year` + `form` (mirroring how the worker
 * resolves a filing), so we match on both shapes. Only PENDING jobs are touched;
 * in-flight/backoff jobs are left alone. Returns the number of jobs bumped.
 */
export async function prioritizeFilingAnalysis(input: PrioritizeFilingInput): Promise<number> {
	const ticker = input.ticker.toUpperCase();
	const years = [...new Set(input.years.filter((y) => Number.isFinite(y)))].map((y) => String(y));

	// Match by ticker+form+year only when we actually have year(s); otherwise the
	// IN (...) list would be empty/invalid, so fall back to the accession match.
	const tickerMatch =
		years.length > 0
			? sql`(
					upper(params ->> 'ticker') = ${ticker}
					AND coalesce(params ->> 'form', '10-K') = ${input.form}
					AND params ->> 'year' IN (${sql.join(years.map((y) => sql`${y}`))})
				)`
			: sql`false`;

	const result = await sql<{ id: string }>`
		UPDATE jobs
		SET priority = 0
		WHERE status = 'pending'
			AND (
				params ->> 'accession_number' = ${input.accession}
				OR ${tickerMatch}
			)
		RETURNING id
	`.execute(db);

	return result.rows.length;
}
