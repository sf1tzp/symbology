import { sql } from 'kysely';
import { db } from '../db';
import type {
	FilingResponse,
	FilingTimelineResponse,
	DocumentResponse,
	CompanyResponse
} from '$lib/api-types';

/**
 * Estimate the total document input tokens across a set of filings — the volume
 * of source text the synthesis considered. No per-document token count is stored,
 * so we sum the substantive document content length and approximate at the common
 * ~4 chars/token ratio. Returns 0 for an empty filing set.
 */
export async function getSourceFilingInputTokens(filingIds: string[]): Promise<number> {
	if (filingIds.length === 0) return 0;
	const row = await db
		.selectFrom('documents')
		.select((eb) => eb.fn.sum<number>(sql`char_length(content)`).as('chars'))
		.where('filing_id', 'in', filingIds)
		.where('is_substantive', '=', true)
		.executeTakeFirst();
	const chars = Number(row?.chars ?? 0);
	return Math.round(chars / 4);
}

export async function getFilingsTimeline(
	ticker: string,
	limit: number = 20,
	form?: string | string[]
): Promise<FilingTimelineResponse[]> {
	// 1. Get company ID
	const company = await db
		.selectFrom('companies')
		.select('id')
		.where('ticker', '=', ticker.toUpperCase())
		.executeTakeFirst();

	if (!company) return [];

	// 2. Get filings ordered by period_of_report ASC (optionally filtered by one
	//    form or a set of forms, e.g. ['10-K','10-Q'] for the company timeline).
	let query = db.selectFrom('filings').selectAll().where('company_id', '=', company.id);

	if (Array.isArray(form)) {
		if (form.length > 0) query = query.where('form', 'in', form);
	} else if (form) {
		query = query.where('form', '=', form);
	}

	const filings = await query.orderBy('period_of_report', 'asc').limit(limit).execute();

	if (filings.length === 0) return [];

	const filingIds = filings.map((f) => f.id);

	// 3. Get all documents for these filings (exclude large content column)
	const documents = await db
		.selectFrom('documents')
		.select(['id', 'filing_id', 'title', 'document_type', 'content_hash'])
		.where('filing_id', 'in', filingIds)
		.execute();

	const allDocIds = documents.map((d) => d.id);

	// 4. Batch-fetch generated content for all document IDs (avoids N+1)
	const gcByDocId = new Map<
		string,
		Array<{
			id: string;
			content_hash: string | null;
			short_hash: string | null;
			description: string | null;
			document_type: string | null;
			form_type: string | null;
			content_stage: string | null;
			summary: string | null;
			created_at: string;
		}>
	>();

	if (allDocIds.length > 0) {
		const gcRows = await db
			.selectFrom('generated_content as gc')
			.innerJoin(
				'generated_content_document_association as gcda',
				'gc.id',
				'gcda.generated_content_id'
			)
			.select([
				'gcda.document_id',
				'gc.id',
				'gc.content_hash',
				'gc.description',
				'gc.document_type',
				'gc.form_type',
				'gc.content_stage',
				'gc.summary',
				'gc.created_at'
			])
			.where('gcda.document_id', 'in', allDocIds)
			.execute();

		for (const row of gcRows) {
			const docId = row.document_id;
			if (!gcByDocId.has(docId)) gcByDocId.set(docId, []);
			gcByDocId.get(docId)!.push({
				id: row.id,
				content_hash: row.content_hash,
				short_hash: row.content_hash?.slice(0, 12) ?? null,
				description: row.description,
				document_type: row.document_type,
				form_type: row.form_type,
				content_stage: row.content_stage,
				summary: row.summary,
				created_at: toISOString(row.created_at)
			});
		}
	}

	// 5. Group documents by filing
	const docsByFiling = new Map<string, typeof documents>();
	for (const doc of documents) {
		const fId = doc.filing_id!;
		if (!docsByFiling.has(fId)) docsByFiling.set(fId, []);
		docsByFiling.get(fId)!.push(doc);
	}

	// 6. Assemble nested response
	return filings.map((filing) => ({
		id: filing.id,
		company_id: filing.company_id,
		accession_number: filing.accession_number,
		form: filing.form,
		filing_date: toDateString(filing.filing_date),
		url: filing.url,
		period_of_report: filing.period_of_report ? toDateString(filing.period_of_report) : null,
		documents: (docsByFiling.get(filing.id) ?? []).map((doc) => ({
			id: doc.id,
			title: doc.title,
			document_type: doc.document_type,
			content_hash: doc.content_hash,
			short_hash: doc.content_hash?.slice(0, 12) ?? null,
			generated_content: gcByDocId.get(doc.id) ?? []
		}))
	}));
}

export async function getFilingByAccession(
	accessionNumber: string
): Promise<FilingResponse | null> {
	const filing = await db
		.selectFrom('filings')
		.selectAll()
		.where('accession_number', '=', accessionNumber)
		.executeTakeFirst();

	if (!filing) return null;

	return {
		id: filing.id,
		company_id: filing.company_id,
		accession_number: filing.accession_number,
		form: filing.form,
		filing_date: toDateString(filing.filing_date),
		url: filing.url,
		period_of_report: filing.period_of_report ? toDateString(filing.period_of_report) : null
	};
}

/** DocumentResponse augmented with a flag indicating whether analysis
 * (document page content) has been generated for the document. */
export type DocumentWithAnalysisResponse = DocumentResponse & { has_analysis: boolean };

export async function getDocumentsByAccession(
	accessionNumber: string
): Promise<DocumentWithAnalysisResponse[]> {
	const filing = await db
		.selectFrom('filings')
		.select([
			'id',
			'company_id',
			'accession_number',
			'form',
			'filing_date',
			'url',
			'period_of_report'
		])
		.where('accession_number', '=', accessionNumber)
		.executeTakeFirst();

	if (!filing) return [];

	const documents = await db
		.selectFrom('documents')
		.innerJoin('companies', 'companies.id', 'documents.company_id')
		.select([
			'documents.id',
			'documents.filing_id',
			'documents.title',
			'documents.document_type',
			'documents.content',
			'documents.content_hash',
			'companies.ticker as company_ticker'
		])
		.where('documents.filing_id', '=', filing.id)
		.execute();

	// Determine which documents have analysis generated. A document "has
	// analysis" when a document_page_content row exists for it with resolved
	// summary (L1) or intro (L2) content — mirroring the document page's own
	// hasAnalysis check, driven entirely from the DB.
	const docIds = documents.map((d) => d.id);
	const analysisDocIds = new Set<string>();
	if (docIds.length > 0) {
		const pageRows = await db
			.selectFrom('document_page_content')
			.select(['document_id', 'summary_content_id', 'intro_content_id'])
			.where('document_id', 'in', docIds)
			.execute();
		for (const row of pageRows) {
			if (row.summary_content_id || row.intro_content_id) {
				analysisDocIds.add(row.document_id);
			}
		}
	}

	const filingResponse: FilingResponse = {
		id: filing.id,
		company_id: filing.company_id,
		accession_number: filing.accession_number,
		form: filing.form,
		filing_date: toDateString(filing.filing_date),
		url: filing.url,
		period_of_report: filing.period_of_report ? toDateString(filing.period_of_report) : null
	};

	return documents.map((doc) => ({
		id: doc.id,
		filing_id: doc.filing_id,
		company_ticker: doc.company_ticker,
		title: doc.title,
		document_type: doc.document_type ?? 'unknown',
		content: doc.content,
		content_hash: doc.content_hash,
		short_hash: doc.content_hash?.slice(0, 12) ?? null,
		has_analysis: analysisDocIds.has(doc.id),
		filing: filingResponse
	}));
}

export async function getCompanyByAccession(
	accessionNumber: string
): Promise<CompanyResponse | null> {
	const filing = await db
		.selectFrom('filings')
		.select('company_id')
		.where('accession_number', '=', accessionNumber)
		.executeTakeFirst();

	if (!filing) return null;

	const company = await db
		.selectFrom('companies')
		.selectAll()
		.where('id', '=', filing.company_id)
		.executeTakeFirst();

	if (!company) return null;

	// Fetch frontpage summary
	const summaryRow = await db
		.selectFrom('generated_content')
		.select('content')
		.where('company_id', '=', company.id)
		.where((eb) =>
			eb.or([
				eb.and([
					eb('content_stage', '=', 'frontpage_summary'),
					eb('document_type', '=', 'business_description')
				]),
				eb('description', '=', 'business_description_frontpage_summary')
			])
		)
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();

	return {
		id: company.id,
		name: company.name,
		display_name: company.display_name,
		ticker: company.ticker,
		cik: company.cik,
		exchanges: company.exchanges ?? [],
		sic: company.sic,
		sic_description: company.sic_description,
		fiscal_year_end: company.fiscal_year_end
			? new Date(company.fiscal_year_end as unknown as string).toISOString().split('T')[0]
			: null,
		former_names: (company.former_names as Array<{ name: string; date_changed: string }>) ?? [],
		summary: summaryRow?.content ?? null
	};
}

export async function getFilingsByCompanyId(
	companyId: string,
	excludeAccession?: string,
	limit: number = 10
): Promise<FilingResponse[]> {
	let query = db
		.selectFrom('filings')
		.selectAll()
		.where('company_id', '=', companyId)
		.orderBy('period_of_report', 'desc')
		.limit(limit);

	if (excludeAccession) {
		query = query.where('accession_number', '!=', excludeAccession);
	}

	const filings = await query.execute();

	return filings.map((f) => ({
		id: f.id,
		company_id: f.company_id,
		accession_number: f.accession_number,
		form: f.form,
		filing_date: toDateString(f.filing_date),
		url: f.url,
		period_of_report: f.period_of_report ? toDateString(f.period_of_report) : null
	}));
}

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
