import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';

// Only companies that have generated PageContent are published/discoverable.
// (Reused across the list queries below, which select from `companies as c`.)
const hasPageContent = sql<boolean>`EXISTS (SELECT 1 FROM company_page_content cpc WHERE cpc.company_id = c.id)`;

export const GET: RequestHandler = async ({ url }) => {
	const search = url.searchParams.get('search');
	const skip = Number(url.searchParams.get('skip')) || 0;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 50, 100);
	const sort = url.searchParams.get('sort') || 'ticker';

	if (search && search.trim().length > 0) {
		const [results, total] = await Promise.all([
			searchCompanies(search.trim(), limit, skip),
			countSearchResults(search.trim())
		]);
		return json({ companies: results, total });
	}

	// Build base query with filing metadata
	let query = db
		.selectFrom('companies as c')
		.leftJoin('filings as f', 'f.company_id', 'c.id')
		.select([
			'c.id',
			'c.name',
			'c.display_name',
			'c.ticker',
			'c.exchanges',
			'c.sic',
			'c.sic_description',
			'c.fiscal_year_end',
			'c.former_names',
			sql<number>`count(f.id)::int`.as('filing_count'),
			sql<string>`max(f.filing_date)`.as('last_filing_date'),
			sql<string>`(SELECT f2.form FROM filings f2 WHERE f2.company_id = c.id ORDER BY f2.filing_date DESC LIMIT 1)`.as(
				'last_filing_form'
			)
		])
		.groupBy('c.id')
		.having(sql`count(f.id)`, '>', 0)
		.where(hasPageContent);

	// Apply sort
	if (sort === 'name') {
		query = query.orderBy('c.name', 'asc');
	} else if (sort === 'recent') {
		query = query.orderBy(sql`max(f.filing_date)`, sql`desc nulls last`);
	} else {
		query = query.orderBy('c.ticker', 'asc');
	}

	const [companies, countResult] = await Promise.all([
		query.offset(skip).limit(limit).execute(),
		db
			.selectFrom('companies')
			.select(sql<number>`count(*)::int`.as('total'))
			.where(sql`EXISTS (SELECT 1 FROM company_page_content WHERE company_id = companies.id)`)
			.executeTakeFirstOrThrow()
	]);

	return json({
		companies: companies.map((c) => toCompanyListItem(c)),
		total: countResult.total
	});
};

async function searchCompanies(query: string, limit: number, skip: number = 0) {
	if (query.length < 3) {
		const results = await db
			.selectFrom('companies as c')
			.leftJoin('filings as f', 'f.company_id', 'c.id')
			.select([
				'c.id',
				'c.name',
				'c.display_name',
				'c.ticker',
				'c.exchanges',
				'c.sic',
				'c.sic_description',
				'c.fiscal_year_end',
				'c.former_names',
				sql<number>`count(f.id)::int`.as('filing_count'),
				sql<string>`max(f.filing_date)`.as('last_filing_date'),
				sql<string>`(SELECT f2.form FROM filings f2 WHERE f2.company_id = c.id ORDER BY f2.filing_date DESC LIMIT 1)`.as(
					'last_filing_form'
				)
			])
			.where((eb) =>
				eb.or([eb('c.ticker', 'ilike', `${query}%`), eb('c.name', 'ilike', `${query}%`)])
			)
			.groupBy('c.id')
			.having(sql`count(f.id)`, '>', 0)
			.where(hasPageContent)
			.orderBy('c.ticker', 'asc')
			.offset(skip)
			.limit(limit)
			.execute();

		return results.map(toCompanyListItem);
	}

	// Full-text search
	let results = await db
		.selectFrom('companies as c')
		.leftJoin('filings as f', 'f.company_id', 'c.id')
		.select([
			'c.id',
			'c.name',
			'c.display_name',
			'c.ticker',
			'c.exchanges',
			'c.sic',
			'c.sic_description',
			'c.fiscal_year_end',
			'c.former_names',
			sql<number>`count(f.id)::int`.as('filing_count'),
			sql<string>`max(f.filing_date)`.as('last_filing_date'),
			sql<string>`(SELECT f2.form FROM filings f2 WHERE f2.company_id = c.id ORDER BY f2.filing_date DESC LIMIT 1)`.as(
				'last_filing_form'
			)
		])
		.where(sql<boolean>`c.search_vector @@ websearch_to_tsquery('english', ${query})`)
		.groupBy('c.id')
		.having(sql`count(f.id)`, '>', 0)
		.where(hasPageContent)
		.orderBy(sql`ts_rank(c.search_vector, websearch_to_tsquery('english', ${query}))`, 'desc')
		.offset(skip)
		.limit(limit)
		.execute();

	// Fallback to ILIKE
	if (results.length === 0) {
		results = await db
			.selectFrom('companies as c')
			.leftJoin('filings as f', 'f.company_id', 'c.id')
			.select([
				'c.id',
				'c.name',
				'c.display_name',
				'c.ticker',
				'c.exchanges',
				'c.sic',
				'c.sic_description',
				'c.fiscal_year_end',
				'c.former_names',
				sql<number>`count(f.id)::int`.as('filing_count'),
				sql<string>`max(f.filing_date)`.as('last_filing_date'),
				sql<string>`(SELECT f2.form FROM filings f2 WHERE f2.company_id = c.id ORDER BY f2.filing_date DESC LIMIT 1)`.as(
					'last_filing_form'
				)
			])
			.where((eb) =>
				eb.or([eb('c.ticker', 'ilike', `%${query}%`), eb('c.name', 'ilike', `%${query}%`)])
			)
			.groupBy('c.id')
			.having(sql`count(f.id)`, '>', 0)
			.where(hasPageContent)
			.orderBy('c.ticker', 'asc')
			.offset(skip)
			.limit(limit)
			.execute();
	}

	return results.map(toCompanyListItem);
}

async function countSearchResults(query: string): Promise<number> {
	if (query.length < 3) {
		const result = await db
			.selectFrom('companies')
			.select(sql<number>`count(*)::int`.as('total'))
			.where((eb) => eb.or([eb('ticker', 'ilike', `${query}%`), eb('name', 'ilike', `${query}%`)]))
			.where(sql`EXISTS (SELECT 1 FROM company_page_content WHERE company_id = companies.id)`)
			.executeTakeFirstOrThrow();
		return result.total;
	}

	let result = await db
		.selectFrom('companies')
		.select(sql<number>`count(*)::int`.as('total'))
		.where(sql<boolean>`search_vector @@ websearch_to_tsquery('english', ${query})`)
		.where(sql`EXISTS (SELECT 1 FROM company_page_content WHERE company_id = companies.id)`)
		.executeTakeFirstOrThrow();

	if (result.total === 0) {
		result = await db
			.selectFrom('companies')
			.select(sql<number>`count(*)::int`.as('total'))
			.where((eb) =>
				eb.or([eb('ticker', 'ilike', `%${query}%`), eb('name', 'ilike', `%${query}%`)])
			)
			.where(sql`EXISTS (SELECT 1 FROM company_page_content WHERE company_id = companies.id)`)
			.executeTakeFirstOrThrow();
	}

	return result.total;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toCompanyListItem(c: any) {
	return {
		id: c.id,
		name: c.name,
		display_name: c.display_name,
		ticker: c.ticker,
		exchanges: c.exchanges ?? [],
		sic: c.sic,
		sic_description: c.sic_description,
		fiscal_year_end: c.fiscal_year_end
			? new Date(c.fiscal_year_end as unknown as string).toISOString().split('T')[0]
			: null,
		former_names: c.former_names ?? [],
		summary: null,
		filing_count: c.filing_count ?? 0,
		last_filing_date: c.last_filing_date
			? new Date(c.last_filing_date as unknown as string).toISOString().split('T')[0]
			: null,
		last_filing_form: c.last_filing_form ?? null
	};
}
