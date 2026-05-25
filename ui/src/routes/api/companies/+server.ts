import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';

export const GET: RequestHandler = async ({ url }) => {
	const search = url.searchParams.get('search');
	const skip = Number(url.searchParams.get('skip')) || 0;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 50, 100);

	if (search && search.trim().length > 0) {
		const results = await searchCompanies(search.trim(), limit);
		return json(results);
	}

	// List all companies with pagination
	const companies = await db
		.selectFrom('companies')
		.selectAll()
		.orderBy('ticker', 'asc')
		.offset(skip)
		.limit(limit)
		.execute();

	return json(
		companies.map((c) => ({
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
			summary: null
		}))
	);
};

async function searchCompanies(query: string, limit: number) {
	if (query.length < 3) {
		// Short queries: ticker prefix match
		const results = await db
			.selectFrom('companies')
			.selectAll()
			.where((eb) =>
				eb.or([
					eb('ticker', 'ilike', `${query}%`),
					eb('name', 'ilike', `${query}%`)
				])
			)
			.orderBy('ticker', 'asc')
			.limit(limit)
			.execute();

		return results.map(toCompanyResponse);
	}

	// Longer queries: full-text search
	let results = await db
		.selectFrom('companies')
		.selectAll()
		.where(sql<boolean>`search_vector @@ websearch_to_tsquery('english', ${query})`)
		.orderBy(sql`ts_rank(search_vector, websearch_to_tsquery('english', ${query}))`, 'desc')
		.limit(limit)
		.execute();

	// Fallback to ILIKE if FTS returns nothing
	if (results.length === 0) {
		results = await db
			.selectFrom('companies')
			.selectAll()
			.where((eb) =>
				eb.or([
					eb('ticker', 'ilike', `%${query}%`),
					eb('name', 'ilike', `%${query}%`)
				])
			)
			.orderBy('ticker', 'asc')
			.limit(limit)
			.execute();
	}

	return results.map(toCompanyResponse);
}

function toCompanyResponse(c: any) {
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
		summary: null
	};
}
