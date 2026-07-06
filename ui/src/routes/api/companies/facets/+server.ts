import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';
import { companyIsVisible } from '$lib/server/db/predicates';

/**
 * Facet metadata for the /c browse experience. Currently just the industry
 * facet: the distinct SIC industries (code + description) across the visible,
 * filing-having company universe, with a per-industry company count so the UI
 * can show "Software — 42" and sort the list by prevalence.
 */
export const GET: RequestHandler = async () => {
	const industries = await db
		.selectFrom('companies as c')
		.select(['c.sic', 'c.sic_description', sql<number>`count(*)::int`.as('count')])
		.where(companyIsVisible('c'))
		.where(sql<boolean>`EXISTS (SELECT 1 FROM filings f WHERE f.company_id = c.id)`)
		.where('c.sic', 'is not', null)
		.where('c.sic_description', 'is not', null)
		.groupBy(['c.sic', 'c.sic_description'])
		.orderBy('count', 'desc')
		.orderBy('c.sic_description', 'asc')
		.execute();

	return json({ industries });
};
