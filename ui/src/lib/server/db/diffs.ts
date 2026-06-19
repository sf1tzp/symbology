import { db } from '../db';
import { isNumericNoise } from '$lib/utils/changes';
import type { DocumentTypeEnum } from './types';

export interface DiffOp {
	op: 'equal' | 'insert' | 'delete';
	text: string;
}

export interface SectionDiffView {
	id: string;
	ordinal: number;
	topicId: string | null;
	sectionPath: string | null;
	heading: string | null;
	changeKind: string;
	ops: DiffOp[];
	lengthDelta: number;
	tokensAdded: number;
	tokensRemoved: number;
	truncated: boolean;
	summary: string | null;
}

export interface DiffFilingRef {
	id: string;
	accessionNumber: string;
	form: string;
	filingDate: string | null;
	periodOfReport: string | null;
	/** Short content hash of this filing's document of the diff's type, for deep
	 *  links to /d/{accession}/{hash}. Null when the document can't be resolved. */
	documentHash: string | null;
}

export interface DiffSetView {
	id: string;
	documentType: string;
	counts: Record<string, number>;
	leftFiling: DiffFilingRef | null;
	rightFiling: DiffFilingRef | null;
	topics: SectionDiffView[];
	createdAt: string | null;
}

const toIso = (v: unknown): string | null =>
	v ? new Date(v as string | Date).toISOString() : null;

/**
 * Whether a company has any computed diff set — the visibility gate for the
 * company page and change views. A pending company (diffs but no narrative page
 * content) is visible and renders a slimmed-down page.
 */
export async function companyHasDiffSets(companyId: string, form?: string): Promise<boolean> {
	const row = await db
		.selectFrom('diff_sets')
		.select('id')
		.where('company_id', '=', companyId)
		.$if(!!form, (qb) => qb.where('form', '=', form!))
		.limit(1)
		.executeTakeFirst();
	return !!row;
}

async function loadFilingRefs(
	ids: (string | null)[],
	documentType?: DocumentTypeEnum | string | null
): Promise<Map<string, DiffFilingRef>> {
	const real = ids.filter((x): x is string => x !== null);
	if (real.length === 0) return new Map();
	const rows = await db
		.selectFrom('filings')
		.select(['id', 'accession_number', 'form', 'filing_date', 'period_of_report'])
		.where('id', 'in', real)
		.execute();

	// Resolve each filing's document of the diff's type so each side can deep-link
	// to its own document page (/d/{accession}/{short_hash}).
	const hashByFiling = new Map<string, string>();
	if (documentType) {
		const docs = await db
			.selectFrom('documents')
			.select(['filing_id', 'content_hash'])
			.where('filing_id', 'in', real)
			.where('document_type', '=', documentType as DocumentTypeEnum)
			.execute();
		for (const d of docs) {
			if (d.filing_id && d.content_hash && !hashByFiling.has(d.filing_id)) {
				hashByFiling.set(d.filing_id, d.content_hash.slice(0, 12));
			}
		}
	}

	return new Map(
		rows.map((r) => [
			r.id,
			{
				id: r.id,
				accessionNumber: r.accession_number,
				form: r.form,
				filingDate: toIso(r.filing_date),
				periodOfReport: toIso(r.period_of_report),
				documentHash: hashByFiling.get(r.id) ?? null
			}
		])
	);
}

async function loadSummaries(ids: (string | null)[]): Promise<Map<string, string | null>> {
	const real = ids.filter((x): x is string => x !== null);
	if (real.length === 0) return new Map();
	const rows = await db
		.selectFrom('generated_content')
		.select(['id', 'content'])
		.where('id', 'in', real)
		.execute();
	return new Map(rows.map((r) => [r.id, r.content]));
}

interface DiffSetRow {
	id: string;
	document_type: string;
	counts: unknown;
	left_filing_id: string | null;
	right_filing_id: string | null;
	created_at: unknown;
}

const DIFF_SET_COLUMNS = [
	'id',
	'document_type',
	'counts',
	'left_filing_id',
	'right_filing_id',
	'created_at'
] as const;

/** Assemble a full DiffSetView (section diffs + filing refs + summaries) for one set row. */
async function buildDiffSetView(set: DiffSetRow): Promise<DiffSetView> {
	const sections = await db
		.selectFrom('section_diffs')
		.select([
			'id',
			'ordinal',
			'topic_id',
			'section_path',
			'heading',
			'change_kind',
			'ops',
			'length_delta',
			'tokens_added',
			'tokens_removed',
			'truncated',
			'summary_content_id'
		])
		.where('diff_set_id', '=', set.id)
		.orderBy('ordinal', 'asc')
		.execute();

	const [filings, summaries] = await Promise.all([
		loadFilingRefs([set.left_filing_id, set.right_filing_id], set.document_type),
		loadSummaries(sections.map((s) => s.summary_content_id))
	]);

	return {
		id: set.id,
		documentType: set.document_type,
		counts: (set.counts ?? {}) as Record<string, number>,
		leftFiling: set.left_filing_id ? (filings.get(set.left_filing_id) ?? null) : null,
		rightFiling: set.right_filing_id ? (filings.get(set.right_filing_id) ?? null) : null,
		createdAt: toIso(set.created_at),
		topics: sections.map((s) => ({
			id: s.id,
			ordinal: s.ordinal,
			topicId: s.topic_id,
			sectionPath: s.section_path,
			heading: s.heading,
			changeKind: s.change_kind,
			ops: (s.ops ?? []) as unknown as DiffOp[],
			lengthDelta: s.length_delta ?? 0,
			tokensAdded: s.tokens_added ?? 0,
			tokensRemoved: s.tokens_removed ?? 0,
			truncated: s.truncated,
			summary: s.summary_content_id ? (summaries.get(s.summary_content_id) ?? null) : null
		}))
	};
}

/**
 * The most recent precomputed year-over-year diff for a company's section
 * (document type). Returns null when no diff has been computed.
 */
export async function getLatestDiffSet(
	companyId: string,
	documentType: DocumentTypeEnum | string
): Promise<DiffSetView | null> {
	const set = await db
		.selectFrom('diff_sets')
		.select(DIFF_SET_COLUMNS)
		.where('company_id', '=', companyId)
		.where('document_type', '=', documentType as DocumentTypeEnum)
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();
	if (!set) return null;
	return buildDiffSetView(set);
}

/**
 * All diff sets whose *newer* side is the given filing — i.e. "what changed in
 * this filing vs. the immediately prior one", one per document type. Empty when
 * the filing is a company's first of its form.
 */
export async function getDiffSetsByRightFiling(rightFilingId: string): Promise<DiffSetView[]> {
	const sets = await db
		.selectFrom('diff_sets')
		.select(DIFF_SET_COLUMNS)
		.where('right_filing_id', '=', rightFilingId)
		.orderBy('document_type', 'asc')
		.execute();
	return Promise.all(sets.map((s) => buildDiffSetView(s)));
}

/**
 * The chain of consecutive year-over-year diff sets for one section, oldest →
 * newest. Powers the multi-year change report. Limited to the most recent
 * `limit` pairings.
 */
export async function getDiffSetChain(
	companyId: string,
	documentType: DocumentTypeEnum | string,
	limit = 6,
	form?: string
): Promise<DiffSetView[]> {
	const sets = await db
		.selectFrom('diff_sets')
		.select(DIFF_SET_COLUMNS)
		.where('company_id', '=', companyId)
		.where('document_type', '=', documentType as DocumentTypeEnum)
		.$if(!!form, (qb) => qb.where('form', '=', form!))
		.orderBy('created_at', 'desc')
		.limit(limit)
		.execute();
	const views = await Promise.all(sets.map((s) => buildDiffSetView(s)));
	return views.reverse(); // oldest → newest for display
}

// Significance weights per change kind (ordering only; tune freely). Mirrors the
// New / Escalated / … priority of the change cards.
const KIND_WEIGHT: Record<string, number> = {
	new: 1000,
	removed: 900,
	escalated: 600,
	de_emphasised: 500,
	reworded: 200,
	unchanged: 0
};

/**
 * Read-time "analyst significance" heuristic for ranking change cards. A single
 * definition shared by every surface that needs ordering — kind weight plus the
 * volume of edited text. No stored score / migration required.
 */
export function scoreSectionDiff(sd: {
	changeKind: string;
	tokensAdded: number;
	tokensRemoved: number;
	lengthDelta: number;
}): number {
	const kind = KIND_WEIGHT[sd.changeKind] ?? 100;
	return kind + sd.tokensAdded + sd.tokensRemoved + Math.abs(sd.lengthDelta) * 0.1;
}

export interface ChangeCardView {
	id: string; // section_diff id → deep-link target (#diff-{id})
	documentType: DocumentTypeEnum | string;
	changeKind: string;
	heading: string | null;
	sectionPath: string | null;
	summary: string | null;
	topicId: string | null;
	rightFiling: DiffFilingRef | null;
	score: number;
}

// Change kinds surfaced as "what's new" cards — shifts in emphasis and wording
// of existing disclosures. New/removed topics are intentionally excluded.
export const CARD_CHANGE_KINDS = ['escalated', 'de_emphasised', 'reworded'] as const;

/**
 * Top-N "what's new" change cards for a company, drawn across all document types
 * from each type's latest diff set, ranked by significance. Limited to the
 * escalated / de-emphasised / reworded kinds (see CARD_CHANGE_KINDS). Empty when
 * the company has no computed diffs (e.g. <2 filings).
 */
export async function getLatestChangeCards(
	companyId: string,
	limit = 6,
	form?: string
): Promise<ChangeCardView[]> {
	// Latest diff set per document type for the company (optionally for one form).
	const sets = await db
		.selectFrom('diff_sets')
		.select(['id', 'document_type', 'right_filing_id'])
		.where('company_id', '=', companyId)
		.$if(!!form, (qb) => qb.where('form', '=', form!))
		.distinctOn('document_type')
		.orderBy('document_type')
		.orderBy('created_at', 'desc')
		.execute();
	if (sets.length === 0) return [];

	const setMeta = new Map(sets.map((s) => [s.id, s]));
	const sections = await db
		.selectFrom('section_diffs')
		.select([
			'id',
			'diff_set_id',
			'topic_id',
			'section_path',
			'heading',
			'change_kind',
			'ops',
			'length_delta',
			'tokens_added',
			'tokens_removed',
			'summary_content_id'
		])
		.where(
			'diff_set_id',
			'in',
			sets.map((s) => s.id)
		)
		.where('change_kind', 'in', [...CARD_CHANGE_KINDS])
		.execute();
	// Drop figures-only changes (year-over-year tables) — same gate the on-page
	// listings apply, here on the server since cards are assembled without ops.
	const visible = sections.filter((s) => !isNumericNoise(s.ops as unknown as DiffOp[]));
	if (visible.length === 0) return [];

	const [filings, summaries] = await Promise.all([
		loadFilingRefs(sets.map((s) => s.right_filing_id)),
		loadSummaries(visible.map((s) => s.summary_content_id))
	]);

	const cards: ChangeCardView[] = visible.map((s) => {
		const meta = setMeta.get(s.diff_set_id);
		const rightId = meta?.right_filing_id ?? null;
		return {
			id: s.id,
			documentType: meta?.document_type ?? '',
			changeKind: s.change_kind,
			heading: s.heading,
			sectionPath: s.section_path,
			summary: s.summary_content_id ? (summaries.get(s.summary_content_id) ?? null) : null,
			topicId: s.topic_id,
			rightFiling: rightId ? (filings.get(rightId) ?? null) : null,
			score: scoreSectionDiff({
				changeKind: s.change_kind,
				tokensAdded: s.tokens_added ?? 0,
				tokensRemoved: s.tokens_removed ?? 0,
				lengthDelta: s.length_delta ?? 0
			})
		};
	});

	cards.sort((a, b) => b.score - a.score);
	return cards.slice(0, limit);
}
