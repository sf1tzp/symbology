import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { sql } from 'kysely';
import type { SynthesisListItem } from '$lib/api-types';

// The user-facing synthesis stages surfaced on the /s browse index. Internal
// fragments (intros, frontpage/aggregate summaries) are excluded — these are the
// substantive, standalone pieces a reader would open on their own.
const VISIBLE_STAGES = [
	'company_main_content',
	'filing_main_content',
	'group_main_content',
	'change_report',
	'topic_diff_summary',
	'company_group_analysis'
] as const;

/**
 * Paginated, searchable list of syntheses for the /s browse index. Mirrors the
 * companies list endpoint shape: `{ syntheses, total }` with `skip` / `limit` /
 * `search`. Newest first; search matches the subject company ticker / name or
 * group name. Only hash-addressable, company- or group-scoped content is shown.
 */
export const GET: RequestHandler = async ({ url }) => {
	const search = (url.searchParams.get('search') ?? '').trim();
	const skip = Number(url.searchParams.get('skip')) || 0;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 30, 100);

	let base = db
		.selectFrom('generated_content as gc')
		.leftJoin('companies as c', 'c.id', 'gc.company_id')
		.leftJoin('company_groups as g', 'g.id', 'gc.company_group_id')
		.where('gc.content_hash', 'is not', null)
		.where('gc.content_stage', 'in', VISIBLE_STAGES)
		.where((eb) =>
			eb.or([eb('gc.company_id', 'is not', null), eb('gc.company_group_id', 'is not', null)])
		);

	if (search) {
		base = base.where((eb) =>
			eb.or([
				eb('c.ticker', 'ilike', `${search}%`),
				eb('c.name', 'ilike', `%${search}%`),
				eb('g.name', 'ilike', `%${search}%`)
			])
		);
	}

	const [rows, countResult] = await Promise.all([
		base
			.select([
				'gc.content_hash',
				'gc.content_stage',
				'gc.form_type',
				'gc.generation_depth',
				'gc.created_at',
				'c.ticker as company_ticker',
				'c.name as company_name',
				'c.display_name as company_display_name',
				'g.name as group_name'
			])
			.orderBy('gc.created_at', 'desc')
			.offset(skip)
			.limit(limit)
			.execute(),
		base.select(sql<number>`count(*)::int`.as('total')).executeTakeFirstOrThrow()
	]);

	const syntheses: SynthesisListItem[] = rows.map((r) => ({
		short_hash: r.content_hash!.slice(0, 12),
		content_stage: r.content_stage,
		form_type: r.form_type,
		generation_depth: r.generation_depth,
		created_at: toISOString(r.created_at),
		scope_label:
			r.company_display_name || r.company_name || r.group_name || r.company_ticker || '—',
		scope_ticker: r.company_ticker ?? null
	}));

	return json({ syntheses, total: countResult.total });
};

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}
