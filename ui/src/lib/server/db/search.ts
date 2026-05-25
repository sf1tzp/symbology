import { db } from '../db';
import { sql, type RawBuilder } from 'kysely';
import type { SearchResponse } from '$lib/api-types';

interface SearchOptions {
	entityTypes?: string[];
	sic?: string;
	formType?: string;
	documentType?: string;
	dateFrom?: string;
	dateTo?: string;
	limit?: number;
	offset?: number;
}

export async function unifiedSearch(query: string, options: SearchOptions = {}): Promise<SearchResponse> {
	const {
		entityTypes = ['company', 'filing', 'generated_content', 'company_group'],
		sic,
		formType,
		documentType,
		dateFrom,
		dateTo,
		limit = 20,
		offset = 0
	} = options;

	// Use a single raw SQL query with proper parameterization via Kysely's sql tag
	const parts: RawBuilder<unknown>[] = [];

	if (entityTypes.includes('company')) {
		let q = sql`
			SELECT 'company' as entity_type, id::text,
				ts_rank(search_vector, websearch_to_tsquery('english', ${query})) as rank,
				ts_headline('english', concat_ws(' ', name, ticker, sic_description),
					websearch_to_tsquery('english', ${query}),
					'MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>') as headline,
				name as title, ticker as subtitle, null::text as date_value
			FROM companies
			WHERE search_vector @@ websearch_to_tsquery('english', ${query})
		`;
		if (sic) {
			q = sql`${q} AND sic = ${sic}`;
		}
		parts.push(q);
	}

	if (entityTypes.includes('filing')) {
		let q = sql`
			SELECT 'filing' as entity_type, id::text,
				ts_rank(search_vector, websearch_to_tsquery('english', ${query})) as rank,
				ts_headline('english', concat_ws(' ', accession_number, form),
					websearch_to_tsquery('english', ${query}),
					'MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>') as headline,
				form as title, accession_number as subtitle, filing_date::text as date_value
			FROM filings
			WHERE search_vector @@ websearch_to_tsquery('english', ${query})
		`;
		if (formType) {
			q = sql`${q} AND form = ${formType}`;
		}
		if (dateFrom) {
			q = sql`${q} AND filing_date >= ${dateFrom}::date`;
		}
		if (dateTo) {
			q = sql`${q} AND filing_date <= ${dateTo}::date`;
		}
		parts.push(q);
	}

	if (entityTypes.includes('generated_content')) {
		let q = sql`
			SELECT 'generated_content' as entity_type, id::text,
				ts_rank(search_vector, websearch_to_tsquery('english', ${query})) as rank,
				ts_headline('english', concat_ws(' ', summary, description),
					websearch_to_tsquery('english', ${query}),
					'MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>') as headline,
				description as title, form_type as subtitle, created_at::text as date_value
			FROM generated_content
			WHERE search_vector @@ websearch_to_tsquery('english', ${query})
		`;
		if (documentType) {
			q = sql`${q} AND document_type = ${documentType}`;
		}
		if (dateFrom) {
			q = sql`${q} AND created_at >= ${dateFrom}::date`;
		}
		if (dateTo) {
			q = sql`${q} AND created_at <= ${dateTo}::date`;
		}
		parts.push(q);
	}

	if (entityTypes.includes('company_group')) {
		const q = sql`
			SELECT 'company_group' as entity_type, id::text,
				ts_rank(search_vector, websearch_to_tsquery('english', ${query})) as rank,
				ts_headline('english', concat_ws(' ', name, slug, description),
					websearch_to_tsquery('english', ${query}),
					'MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>') as headline,
				name as title, slug as subtitle, created_at::text as date_value
			FROM company_groups
			WHERE search_vector @@ websearch_to_tsquery('english', ${query})
		`;
		parts.push(q);
	}

	if (parts.length === 0) {
		return { results: [], total: 0, query };
	}

	// Build UNION ALL by joining the compiled parts
	const combined = parts.length === 1
		? parts[0]
		: parts.reduce((acc, part, i) => i === 0 ? part : sql`${acc} UNION ALL ${part}`);

	// Count total
	const countResult = await sql<{ count: string }>`
		SELECT count(*) as count FROM (${combined}) as combined
	`.execute(db);
	const total = Number(countResult.rows[0]?.count ?? 0);

	// Fetch paginated results
	const results = await sql<{
		entity_type: string;
		id: string;
		rank: number;
		headline: string | null;
		title: string | null;
		subtitle: string | null;
		date_value: string | null;
	}>`
		SELECT * FROM (${combined}) as combined
		ORDER BY rank DESC
		LIMIT ${limit} OFFSET ${offset}
	`.execute(db);

	return {
		results: results.rows.map((r) => ({
			entity_type: r.entity_type,
			id: r.id,
			rank: Number(r.rank),
			headline: r.headline,
			title: r.title,
			subtitle: r.subtitle,
			date_value: r.date_value ? String(r.date_value).split('T')[0] : null
		})),
		total,
		query
	};
}
