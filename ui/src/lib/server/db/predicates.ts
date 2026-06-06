import { sql, type RawBuilder } from 'kysely';

/**
 * A company is "visible" (published / discoverable) once it has at least one
 * computed diff set — its filing timeline, finances, and "what's new" cards all
 * render without narrative page content. The `company_page_content` arm is a
 * safety net: inline diff generation during company-page generation is
 * non-fatal, so a fully-published company could theoretically lack `diff_sets`
 * and must never be hidden.
 *
 * `alias` is the outer table alias the surrounding query gives `companies`
 * (e.g. `c` in the list queries, `companies` in the count/search queries).
 */
export function companyIsVisible(alias: string): RawBuilder<boolean> {
	const ref = sql.ref(`${alias}.id`);
	return sql<boolean>`(
		EXISTS (SELECT 1 FROM diff_sets ds WHERE ds.company_id = ${ref})
		OR EXISTS (SELECT 1 FROM company_page_content cpc WHERE cpc.company_id = ${ref})
	)`;
}
