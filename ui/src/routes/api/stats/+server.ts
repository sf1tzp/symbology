import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';

export const GET: RequestHandler = async () => {
	const [companies, filings, documents, earliestFiling] = await Promise.all([
		db
			.selectFrom('companies')
			.select(sql<number>`count(*)::int`.as('count'))
			.executeTakeFirstOrThrow(),
		db
			.selectFrom('filings')
			.select(sql<number>`count(*)::int`.as('count'))
			.executeTakeFirstOrThrow(),
		db
			.selectFrom('documents')
			.select(sql<number>`count(*)::int`.as('count'))
			.executeTakeFirstOrThrow(),
		db
			.selectFrom('filings')
			.select('filing_date')
			.orderBy('filing_date', 'asc')
			.limit(1)
			.executeTakeFirst()
	]);

	const earliestYear = earliestFiling?.filing_date
		? new Date(earliestFiling.filing_date as unknown as string).getFullYear()
		: null;

	return json({
		companies: companies.count,
		filings: filings.count,
		documents: documents.count,
		earliest_year: earliestYear
	});
};
