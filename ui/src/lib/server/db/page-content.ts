import { sql } from 'kysely';
import { db } from '../db';
import type { FeaturedCompanyIntro } from '$lib/api-types';

export interface PageContentSlot {
	content: string | null;
	contentHash: string | null;
	generationDepth: number | null;
	model: string | null;
}

export interface FilingPageContentResponse {
	id: string;
	createdAt: string | null;
	intro: PageContentSlot | null;
	main: PageContentSlot | null;
}

export interface DocumentPageContentResponse {
	id: string;
	createdAt: string | null;
	intro: PageContentSlot | null;
	summary: PageContentSlot | null;
}

export interface ChangeReportSlot {
	documentType: string;
	report: PageContentSlot | null;
	intro: PageContentSlot | null;
}

export interface CompanyPageContentResponse {
	id: string;
	createdAt: string | null;
	intro: PageContentSlot | null;
	main: PageContentSlot | null;
	changeReports: ChangeReportSlot[];
	sourceFilingIds: string[];
}

/** Resolve a set of generated_content ids into a id -> slot map. */
async function loadSlots(ids: (string | null)[]): Promise<Map<string, PageContentSlot>> {
	const real = ids.filter((x): x is string => x !== null);
	if (real.length === 0) return new Map();
	const rows = await db
		.selectFrom('generated_content as gc')
		.leftJoin('model_configs as mc', 'mc.id', 'gc.model_config_id')
		.select(['gc.id', 'gc.content', 'gc.content_hash', 'gc.generation_depth', 'mc.model'])
		.where('gc.id', 'in', real)
		.execute();
	return new Map(
		rows.map((r) => [
			r.id,
			{
				content: r.content,
				contentHash: r.content_hash,
				generationDepth: r.generation_depth,
				model: r.model
			}
		])
	);
}

const slotFrom = (map: Map<string, PageContentSlot>, id: string | null): PageContentSlot | null =>
	id ? (map.get(id) ?? null) : null;

const toIso = (v: unknown): string | null =>
	v ? new Date(v as string | Date).toISOString() : null;

/**
 * The current (latest) published FilingPageContent for a filing, with its
 * intro (L3) and main (L2) content resolved from generated_content.
 */
export async function getCurrentFilingPageContent(
	filingId: string
): Promise<FilingPageContentResponse | null> {
	const page = await db
		.selectFrom('filing_page_content')
		.select(['id', 'main_content_id', 'intro_content_id', 'created_at'])
		.where('filing_id', '=', filingId)
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();
	if (!page) return null;

	const slots = await loadSlots([page.main_content_id, page.intro_content_id]);
	return {
		id: page.id,
		createdAt: toIso(page.created_at),
		intro: slotFrom(slots, page.intro_content_id),
		main: slotFrom(slots, page.main_content_id)
	};
}

/**
 * The current (latest) published DocumentPageContent for a document, with its
 * intro (L2) and L1 summary content resolved from generated_content.
 */
export async function getCurrentDocumentPageContent(
	documentId: string
): Promise<DocumentPageContentResponse | null> {
	const page = await db
		.selectFrom('document_page_content')
		.select(['id', 'summary_content_id', 'intro_content_id', 'created_at'])
		.where('document_id', '=', documentId)
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();
	if (!page) return null;

	const slots = await loadSlots([page.summary_content_id, page.intro_content_id]);
	return {
		id: page.id,
		createdAt: toIso(page.created_at),
		intro: slotFrom(slots, page.intro_content_id),
		summary: slotFrom(slots, page.summary_content_id)
	};
}

/**
 * The current (latest) published CompanyPageContent for a company, with its
 * intro (L4) + main (L3) content, per-document-type change reports (L2 report +
 * L3 intro), and source-filing provenance, all resolved from generated_content.
 */
export async function getCurrentCompanyPageContent(
	companyId: string
): Promise<CompanyPageContentResponse | null> {
	const page = await db
		.selectFrom('company_page_content')
		.select(['id', 'main_content_id', 'intro_content_id', 'created_at'])
		.where('company_id', '=', companyId)
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();
	if (!page) return null;

	const [reports, filings] = await Promise.all([
		db
			.selectFrom('company_page_content_change_report')
			.select(['document_type', 'change_report_id', 'change_report_intro_id'])
			.where('company_page_content_id', '=', page.id)
			.execute(),
		db
			.selectFrom('company_page_content_filing')
			.select('filing_id')
			.where('company_page_content_id', '=', page.id)
			.execute()
	]);

	const slots = await loadSlots([
		page.main_content_id,
		page.intro_content_id,
		...reports.flatMap((r) => [r.change_report_id, r.change_report_intro_id])
	]);

	return {
		id: page.id,
		createdAt: toIso(page.created_at),
		intro: slotFrom(slots, page.intro_content_id),
		main: slotFrom(slots, page.main_content_id),
		changeReports: reports.map((r) => ({
			documentType: r.document_type,
			report: slotFrom(slots, r.change_report_id),
			intro: slotFrom(slots, r.change_report_intro_id)
		})),
		sourceFilingIds: filings.map((f) => f.filing_id)
	};
}

/**
 * Featured companies for the landing carousel: a random selection of published
 * companies (one CompanyPageContent each, its latest), each with its intro text
 * plus the form type and count of the source filings it was synthesised from.
 */
export async function getFeaturedCompanyIntros(limit = 3): Promise<FeaturedCompanyIntro[]> {
	// Latest published page content per company (distinct on company, newest row).
	const latestPerCompany = db
		.selectFrom('company_page_content as cpc')
		.select(['cpc.id', 'cpc.company_id', 'cpc.intro_content_id', 'cpc.created_at'])
		.distinctOn('cpc.company_id')
		.orderBy('cpc.company_id')
		.orderBy('cpc.created_at', 'desc');

	const pages = await db
		.selectFrom(latestPerCompany.as('p'))
		.innerJoin('companies as c', 'c.id', 'p.company_id')
		.select([
			'p.id',
			'p.intro_content_id',
			'p.created_at',
			'c.ticker',
			'c.name',
			'c.display_name',
			'c.sic_description'
		])
		.where('p.intro_content_id', 'is not', null)
		.orderBy(sql`random()`)
		.limit(limit)
		.execute();

	if (pages.length === 0) return [];

	const pageIds = pages.map((p) => p.id);
	const [introSlots, sourceRows] = await Promise.all([
		loadSlots(pages.map((p) => p.intro_content_id)),
		db
			.selectFrom('company_page_content_filing as cpcf')
			.innerJoin('filings as f', 'f.id', 'cpcf.filing_id')
			.select(['cpcf.company_page_content_id as pageId', 'f.form'])
			.where('cpcf.company_page_content_id', 'in', pageIds)
			.execute()
	]);

	// Aggregate source filings per page: how many, and the dominant form type.
	const sourcesByPage = new Map<string, { count: number; forms: Map<string, number> }>();
	for (const row of sourceRows) {
		const agg = sourcesByPage.get(row.pageId) ?? { count: 0, forms: new Map<string, number>() };
		agg.count += 1;
		agg.forms.set(row.form, (agg.forms.get(row.form) ?? 0) + 1);
		sourcesByPage.set(row.pageId, agg);
	}
	const dominantForm = (forms: Map<string, number>): string | null => {
		let best: string | null = null;
		let bestN = 0;
		for (const [form, n] of forms) {
			if (n > bestN) {
				best = form;
				bestN = n;
			}
		}
		return best;
	};

	return pages.map((p) => {
		const agg = sourcesByPage.get(p.id);
		return {
			ticker: p.ticker,
			name: p.name,
			display_name: p.display_name,
			sic_description: p.sic_description,
			intro: slotFrom(introSlots, p.intro_content_id)?.content ?? null,
			source_form_type: agg ? dominantForm(agg.forms) : null,
			source_filing_count: agg?.count ?? 0,
			created_at: toIso(p.created_at)
		};
	});
}
