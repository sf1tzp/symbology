import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql, type RawBuilder } from 'kysely';
import { companyIsVisible } from '$lib/server/db/predicates';

export const GET: RequestHandler = async ({ url }) => {
	const search = url.searchParams.get('search');
	const skip = Number(url.searchParams.get('skip')) || 0;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 50, 100);
	const sort = url.searchParams.get('sort') || 'ticker';
	const filters: CompanyFilters = {
		sic: url.searchParams.get('sic')?.trim() || null,
		content: parseContent(url.searchParams.get('content'))
	};

	if (search && search.trim().length > 0) {
		const [results, total] = await Promise.all([
			searchCompanies(search.trim(), limit, skip, filters),
			countSearchResults(search.trim(), filters)
		]);
		return json({ companies: await attachContentFlags(results), total });
	}

	// Build the base list query with filing metadata, then layer on the facet
	// filters (industry + available content types).
	let query = applyCompanyFilters(baseCompanyQuery(), 'c', filters);

	// Apply sort
	if (sort === 'name') {
		query = query.orderBy('c.name', 'asc');
	} else if (sort === 'recent') {
		query = query.orderBy(sql`max(f.filing_date)`, sql`desc nulls last`);
	} else {
		query = query.orderBy('c.ticker', 'asc');
	}

	const [companies, total] = await Promise.all([
		query.offset(skip).limit(limit).execute(),
		countCompanies(filters)
	]);

	return json({
		companies: await attachContentFlags(companies.map((c) => toCompanyListItem(c))),
		total
	});
};

type ContentFlag = '10k' | '10q' | 'diffs';

interface CompanyFilters {
	/** SIC industry code to restrict to, or null for all industries. */
	sic: string | null;
	/** Content types the company must have (all of them — AND semantics). */
	content: ContentFlag[];
}

/** Parse the comma-separated `content` param into a deduped list of known flags. */
function parseContent(raw: string | null): ContentFlag[] {
	if (!raw) return [];
	const out: ContentFlag[] = [];
	for (const part of raw.split(',')) {
		const p = part.trim().toLowerCase();
		if ((p === '10k' || p === '10q' || p === 'diffs') && !out.includes(p)) out.push(p);
	}
	return out;
}

/**
 * The shared column set for a company list row — the nine company columns plus
 * derived filing metadata. Factored out so the list, search, and fallback
 * queries stay identical and the facet filters compose onto all of them.
 */
function baseCompanyQuery() {
	return db
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
		.where(companyIsVisible('c'));
}

/**
 * A company row has the given content type. `alias` is whatever the surrounding
 * query calls the `companies` table (`c` in the list/search queries,
 * `companies` in the count queries). Expressed as EXISTS subqueries so they
 * compose onto grouped and ungrouped queries alike.
 */
function contentPredicate(alias: string, flag: ContentFlag): RawBuilder<boolean> {
	const ref = sql.ref(`${alias}.id`);
	if (flag === 'diffs') {
		return sql<boolean>`EXISTS (SELECT 1 FROM diff_sets ds WHERE ds.company_id = ${ref})`;
	}
	const form = flag === '10k' ? '10-K' : '10-Q';
	return sql<boolean>`EXISTS (SELECT 1 FROM company_page_content cpc WHERE cpc.company_id = ${ref} AND cpc.form = ${form})`;
}

/**
 * The company has at least one filing — lets the count queries mirror the list's
 * `having count(f) > 0` without needing the join + group by.
 */
function hasFilings(alias: string): RawBuilder<boolean> {
	return sql<boolean>`EXISTS (SELECT 1 FROM filings f WHERE f.company_id = ${sql.ref(`${alias}.id`)})`;
}

/** Compose the industry + content facet filters onto any company query. */
function applyCompanyFilters<Q>(query: Q, alias: string, filters: CompanyFilters): Q {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let q = query as any;
	if (filters.sic) {
		q = q.where(sql<boolean>`${sql.ref(`${alias}.sic`)} = ${filters.sic}`);
	}
	for (const flag of filters.content) {
		q = q.where(contentPredicate(alias, flag));
	}
	return q as Q;
}

/**
 * Total visible companies that have at least one filing and match the active
 * facet filters. Mirrors the list query's `having count(f) > 0` via a filings
 * EXISTS so pagination totals line up with the rows actually returned.
 */
async function countCompanies(filters: CompanyFilters): Promise<number> {
	const query = applyCompanyFilters(
		db
			.selectFrom('companies as c')
			.select(sql<number>`count(*)::int`.as('total'))
			.where(companyIsVisible('c'))
			.where(hasFilings('c')),
		'c',
		filters
	);
	const result = await query.executeTakeFirstOrThrow();
	return result.total;
}

/**
 * Enrich a page of company list items with flags describing which content types
 * exist for each — the same content surfaced on the c/[ticker] route. Done as a
 * couple of bulk queries over the page's company ids rather than per-row
 * subqueries so it stays cheap regardless of which list/search query produced
 * the rows.
 */
async function attachContentFlags<T extends { id: string }>(companies: T[]) {
	if (companies.length === 0) return companies;
	const ids = companies.map((c) => c.id);

	const [pageRows, diffRows] = await Promise.all([
		db
			.selectFrom('company_page_content')
			.select(['company_id', 'form'])
			.where('company_id', 'in', ids)
			.distinct()
			.execute(),
		db
			.selectFrom('diff_sets')
			.select('company_id')
			.where('company_id', 'in', ids)
			.distinct()
			.execute()
	]);

	const has10k = new Set(pageRows.filter((r) => r.form === '10-K').map((r) => r.company_id));
	const has10q = new Set(pageRows.filter((r) => r.form === '10-Q').map((r) => r.company_id));
	const hasDiffs = new Set(diffRows.map((r) => r.company_id));

	return companies.map((c) => ({
		...c,
		has_10k_page: has10k.has(c.id),
		has_10q_page: has10q.has(c.id),
		has_diffs: hasDiffs.has(c.id)
	}));
}

async function searchCompanies(
	query: string,
	limit: number,
	skip: number = 0,
	filters: CompanyFilters
) {
	if (query.length < 3) {
		const results = await applyCompanyFilters(
			baseCompanyQuery().where((eb) =>
				eb.or([eb('c.ticker', 'ilike', `${query}%`), eb('c.name', 'ilike', `${query}%`)])
			),
			'c',
			filters
		)
			.orderBy('c.ticker', 'asc')
			.offset(skip)
			.limit(limit)
			.execute();

		return results.map(toCompanyListItem);
	}

	// Full-text search
	let results = await applyCompanyFilters(
		baseCompanyQuery().where(
			sql<boolean>`c.search_vector @@ websearch_to_tsquery('english', ${query})`
		),
		'c',
		filters
	)
		.orderBy(sql`ts_rank(c.search_vector, websearch_to_tsquery('english', ${query}))`, 'desc')
		.offset(skip)
		.limit(limit)
		.execute();

	// Fallback to ILIKE
	if (results.length === 0) {
		results = await applyCompanyFilters(
			baseCompanyQuery().where((eb) =>
				eb.or([eb('c.ticker', 'ilike', `%${query}%`), eb('c.name', 'ilike', `%${query}%`)])
			),
			'c',
			filters
		)
			.orderBy('c.ticker', 'asc')
			.offset(skip)
			.limit(limit)
			.execute();
	}

	return results.map(toCompanyListItem);
}

async function countSearchResults(query: string, filters: CompanyFilters): Promise<number> {
	const base = () =>
		applyCompanyFilters(
			db
				.selectFrom('companies')
				.select(sql<number>`count(*)::int`.as('total'))
				.where(companyIsVisible('companies'))
				.where(hasFilings('companies')),
			'companies',
			filters
		);

	if (query.length < 3) {
		const result = await base()
			.where((eb) =>
				eb.or([
					eb('companies.ticker', 'ilike', `${query}%`),
					eb('companies.name', 'ilike', `${query}%`)
				])
			)
			.executeTakeFirstOrThrow();
		return result.total;
	}

	let result = await base()
		.where(sql<boolean>`companies.search_vector @@ websearch_to_tsquery('english', ${query})`)
		.executeTakeFirstOrThrow();

	if (result.total === 0) {
		result = await base()
			.where((eb) =>
				eb.or([
					eb('companies.ticker', 'ilike', `%${query}%`),
					eb('companies.name', 'ilike', `%${query}%`)
				])
			)
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
