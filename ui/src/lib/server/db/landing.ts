import { sql } from 'kysely';
import { db } from '../db';
import { isNumericNoise } from '$lib/utils/changes';
import { cleanContent } from '$lib/utils/filings';
import type { ShowcaseCompany, ShowcaseDiff } from '$lib/api-types';
import {
	CARD_CHANGE_KINDS,
	hasProseEdit,
	isCleanHeading,
	loadFilingRefs,
	loadSummaries,
	scoreSectionDiff,
	type DiffOp
} from './diffs';

// The dossier slide pairs the brief teaser with a diff, so the featured diff
// must stay compact: total rendered text (both sides) under this bound.
const DIFF_MAX_TOTAL_CHARS = 900;
// Random companies sampled before filtering down to `limit` presentable ones.
const COMPANY_POOL = 10;
// How many prose paragraphs of the brief the teaser ships to the client.
const BRIEF_PARAGRAPH_COUNT = 2;
// The showcase is built on the annual narrative: 10-K briefs, 10-K diffs. This
// also keeps "see more changes" deep links valid — the changes page defaults
// to the 10-K form.
const SHOWCASE_FORM = '10-K';

const toIso = (v: unknown): string | null =>
	v ? new Date(v as string | Date).toISOString() : null;

/** First prose paragraphs of the brief markdown (headings/rules skipped). */
function briefTeaser(markdown: string | null): string[] {
	const cleaned = cleanContent(markdown ?? '') ?? '';
	return cleaned
		.split(/\n{2,}/)
		.map((block) => block.trim())
		.filter((block) => block.length > 0 && !/^#{1,6}\s/.test(block) && !/^[-*_\s]{3,}$/.test(block))
		.slice(0, BRIEF_PARAGRAPH_COUNT);
}

/**
 * The landing page's showcase carousel: `limit` randomly selected published
 * companies, each pairing its 10-K brief teaser (first paragraphs + source
 * filings for citation links) with one recent, presentable section diff drawn
 * from the company's latest diff set per document type. Companies with a
 * qualifying diff are preferred; the diff is null when none qualifies yet.
 */
export async function getLandingShowcase(limit = 3): Promise<ShowcaseCompany[]> {
	// Latest published 10-K page per company; random sample of the pool.
	const latestPerCompany = db
		.selectFrom('company_page_content as cpc')
		.select(['cpc.id', 'cpc.company_id', 'cpc.main_content_id', 'cpc.created_at'])
		.where('cpc.form', '=', SHOWCASE_FORM)
		.distinctOn('cpc.company_id')
		.orderBy('cpc.company_id')
		.orderBy('cpc.created_at', 'desc');

	const pages = await db
		.selectFrom(latestPerCompany.as('p'))
		.innerJoin('companies as c', 'c.id', 'p.company_id')
		.select([
			'p.id',
			'p.company_id',
			'p.main_content_id',
			'c.ticker',
			'c.name',
			'c.display_name',
			'c.sic_description',
			'c.fiscal_year_end'
		])
		.where('p.main_content_id', 'is not', null)
		.orderBy(sql`random()`)
		.limit(COMPANY_POOL)
		.execute();
	if (pages.length === 0) return [];

	const companyIds = pages.map((p) => p.company_id);
	const [mainRows, sourceRows, diffSets] = await Promise.all([
		db
			.selectFrom('generated_content')
			.select(['id', 'content'])
			.where(
				'id',
				'in',
				pages.map((p) => p.main_content_id).filter((x): x is string => x !== null)
			)
			.execute(),
		db
			.selectFrom('company_page_content_filing as cpcf')
			.innerJoin('filings as f', 'f.id', 'cpcf.filing_id')
			.select([
				'cpcf.company_page_content_id as pageId',
				'f.accession_number',
				'f.form',
				'f.filing_date',
				'f.period_of_report'
			])
			.where(
				'cpcf.company_page_content_id',
				'in',
				pages.map((p) => p.id)
			)
			.execute(),
		// The "most recent changes" pool: each company's latest diff set per
		// document type.
		db
			.selectFrom('diff_sets')
			.select([
				'id',
				'company_id',
				'document_type',
				'left_filing_id',
				'right_filing_id',
				'created_at'
			])
			.where('company_id', 'in', companyIds)
			.where('form', '=', SHOWCASE_FORM)
			.distinctOn(['company_id', 'document_type'])
			.orderBy('company_id')
			.orderBy('document_type')
			.orderBy('created_at', 'desc')
			.execute()
	]);

	const sections =
		diffSets.length === 0
			? []
			: await db
					.selectFrom('section_diffs')
					.select([
						'id',
						'diff_set_id',
						'section_path',
						'heading',
						'change_kind',
						'ops',
						'truncated',
						'summary_content_id',
						'length_delta',
						'tokens_added',
						'tokens_removed'
					])
					.where(
						'diff_set_id',
						'in',
						diffSets.map((s) => s.id)
					)
					.where('change_kind', 'in', [...CARD_CHANGE_KINDS])
					.where('heading', 'is not', null)
					.where('summary_content_id', 'is not', null)
					.execute();

	const setById = new Map(diffSets.map((s) => [s.id, s]));
	const totalChars = (ops: DiffOp[]) => ops.reduce((n, o) => n + o.text.length, 0);

	// Per company, the compact non-noise candidates: newest diff set first, then
	// most significant edit; picked with progressively relaxed presentability.
	type Candidate = (typeof sections)[number];
	const candidatesByCompany = new Map<string, Candidate[]>();
	for (const s of sections) {
		const ops = s.ops as unknown as DiffOp[];
		if (isNumericNoise(ops) || totalChars(ops) > DIFF_MAX_TOTAL_CHARS) continue;
		const companyId = setById.get(s.diff_set_id)!.company_id;
		const list = candidatesByCompany.get(companyId) ?? [];
		list.push(s);
		candidatesByCompany.set(companyId, list);
	}
	const setTime = (s: Candidate) => {
		const created = setById.get(s.diff_set_id)!.created_at;
		return created ? new Date(created as string | Date).getTime() : 0;
	};
	const score = (s: Candidate) =>
		scoreSectionDiff({
			changeKind: s.change_kind,
			tokensAdded: s.tokens_added ?? 0,
			tokensRemoved: s.tokens_removed ?? 0,
			lengthDelta: s.length_delta ?? 0
		});
	for (const list of candidatesByCompany.values()) {
		list.sort((a, b) => setTime(b) - setTime(a) || score(b) - score(a));
	}
	const pickFor = (companyId: string): Candidate | null => {
		const list = candidatesByCompany.get(companyId);
		if (!list?.length) return null;
		return (
			list.find((c) => hasProseEdit(c.ops as unknown as DiffOp[]) && isCleanHeading(c.heading)) ??
			list.find((c) => hasProseEdit(c.ops as unknown as DiffOp[])) ??
			list[0]
		);
	};

	const contentById = new Map(mainRows.map((r) => [r.id, r.content]));
	const sourcesByPage = new Map<string, typeof sourceRows>();
	for (const row of sourceRows) {
		const list = sourcesByPage.get(row.pageId) ?? [];
		list.push(row);
		sourcesByPage.set(row.pageId, list);
	}

	// Keep companies with a brief teaser; prefer those that also have a diff
	// (stable sort preserves the random order within each group).
	const entries = pages
		.map((p) => ({
			page: p,
			brief: briefTeaser(p.main_content_id ? (contentById.get(p.main_content_id) ?? null) : null),
			pick: pickFor(p.company_id)
		}))
		.filter((e) => e.brief.length > 0)
		.sort((a, b) => Number(!!b.pick) - Number(!!a.pick))
		.slice(0, limit);

	return Promise.all(
		entries.map(async ({ page, brief, pick }): Promise<ShowcaseCompany> => {
			let diff: ShowcaseDiff | null = null;
			if (pick) {
				const set = setById.get(pick.diff_set_id)!;
				const [filings, summaries] = await Promise.all([
					loadFilingRefs([set.left_filing_id, set.right_filing_id], set.document_type),
					loadSummaries([pick.summary_content_id])
				]);
				diff = {
					documentType: set.document_type,
					sectionDiffId: pick.id,
					sectionPath: pick.section_path,
					heading: pick.heading,
					changeKind: pick.change_kind,
					summary: pick.summary_content_id
						? (summaries.get(pick.summary_content_id) ?? null)
						: null,
					ops: (pick.ops ?? []) as unknown as DiffOp[],
					truncated: pick.truncated,
					leftFiling: set.left_filing_id ? (filings.get(set.left_filing_id) ?? null) : null,
					rightFiling: set.right_filing_id ? (filings.get(set.right_filing_id) ?? null) : null
				};
			}

			// Newest-first source filings for the citation chips.
			const sources = [...(sourcesByPage.get(page.id) ?? [])].sort((a, b) => {
				const key = (r: (typeof sourceRows)[number]) =>
					toIso(r.period_of_report ?? r.filing_date) ?? '';
				return key(b).localeCompare(key(a));
			});
			const formCounts = new Map<string, number>();
			for (const s of sources) formCounts.set(s.form, (formCounts.get(s.form) ?? 0) + 1);
			let dominantForm: string | null = null;
			let dominantN = 0;
			for (const [form, n] of formCounts) {
				if (n > dominantN) {
					dominantForm = form;
					dominantN = n;
				}
			}

			return {
				ticker: page.ticker,
				name: page.name,
				display_name: page.display_name,
				sic_description: page.sic_description,
				fiscal_year_end: toIso(page.fiscal_year_end),
				briefParagraphs: brief,
				source_form_type: dominantForm,
				source_filing_count: sources.length,
				sourceFilings: sources.map((s) => ({
					accessionNumber: s.accession_number,
					form: s.form,
					filingDate: toIso(s.filing_date),
					periodOfReport: toIso(s.period_of_report)
				})),
				diff
			};
		})
	);
}
