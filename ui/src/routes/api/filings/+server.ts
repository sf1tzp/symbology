import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';
import { companyIsVisible } from '$lib/server/db/predicates';
import type { FilingListItem } from '$lib/api-types';

// The periodic forms the browse index surfaces — the ones Symbology synthesises.
const FORMS = ['10-K', '10-Q'];

/**
 * Paginated, searchable list of filings for the /f browse index. Mirrors the
 * shape of the companies list endpoint: `{ filings, total }` with `skip` /
 * `limit` / `search` query params. Only filings of visible companies are shown,
 * newest first; search matches company ticker / name or form type.
 */
export const GET: RequestHandler = async ({ url }) => {
	const search = (url.searchParams.get('search') ?? '').trim();
	const skip = Number(url.searchParams.get('skip')) || 0;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 30, 100);

	let base = db
		.selectFrom('filings as f')
		.innerJoin('companies as c', 'c.id', 'f.company_id')
		.where('f.form', 'in', FORMS)
		.where(companyIsVisible('c'));

	if (search) {
		base = base.where((eb) =>
			eb.or([
				eb('c.ticker', 'ilike', `${search}%`),
				eb('c.name', 'ilike', `%${search}%`),
				eb('f.form', 'ilike', `${search}%`)
			])
		);
	}

	const [rows, countResult] = await Promise.all([
		base
			.select([
				'f.id',
				'f.accession_number',
				'f.form',
				'f.filing_date',
				'f.period_of_report',
				'c.ticker as company_ticker',
				'c.name as company_name',
				'c.display_name as company_display_name'
			])
			.orderBy('f.filing_date', 'desc')
			.offset(skip)
			.limit(limit)
			.execute(),
		base.select(sql<number>`count(*)::int`.as('total')).executeTakeFirstOrThrow()
	]);

	// Flag which filings already have a generated synthesis, in one bulk query.
	const filingIds = rows.map((r) => r.id);
	const analysed = new Set<string>();
	if (filingIds.length > 0) {
		const pageRows = await db
			.selectFrom('filing_page_content')
			.select(['filing_id', 'intro_content_id', 'main_content_id'])
			.where('filing_id', 'in', filingIds)
			.execute();
		for (const r of pageRows) {
			if (r.intro_content_id || r.main_content_id) analysed.add(r.filing_id);
		}
	}

	const filings: FilingListItem[] = rows.map((r) => ({
		id: r.id,
		accession_number: r.accession_number,
		form: r.form,
		filing_date: toDateString(r.filing_date),
		period_of_report: r.period_of_report ? toDateString(r.period_of_report) : null,
		company_ticker: r.company_ticker,
		company_name: r.company_name,
		company_display_name: r.company_display_name,
		has_analysis: analysed.has(r.id)
	}));

	return json({ filings, total: countResult.total });
};

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
