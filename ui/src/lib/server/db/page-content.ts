import { db } from '../db';

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

/**
 * A teaser view of page content for the anonymous meter wall: keep the short
 * `intro` lede as a taste, but withhold the full `main` synthesis body. The
 * page renders the intro plus a sign-up LockedBlock in place of the brief.
 */
export function toTeaser<T extends { main: PageContentSlot | null }>(content: T): T {
	return { ...content, main: content.main ? { ...content.main, content: null } : null };
}

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
	companyId: string,
	form?: string
): Promise<CompanyPageContentResponse | null> {
	const page = await db
		.selectFrom('company_page_content')
		.select(['id', 'main_content_id', 'intro_content_id', 'created_at'])
		.where('company_id', '=', companyId)
		.$if(!!form, (qb) => qb.where('form', '=', form!))
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
 * The distinct filing forms a company has published page content for (e.g.
 * ["10-K", "10-Q"]). Drives the page's form toggle — only render it when a
 * company has more than one.
 */
export async function getCompanyPageForms(companyId: string): Promise<string[]> {
	const rows = await db
		.selectFrom('company_page_content')
		.select('form')
		.distinct()
		.where('company_id', '=', companyId)
		.execute();
	return rows.map((r) => r.form);
}
