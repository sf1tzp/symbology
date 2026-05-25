import { db } from '../db';
import type { FilingTimelineResponse } from '$lib/api-types';

export async function getFilingsTimeline(
	ticker: string,
	limit: number = 20
): Promise<FilingTimelineResponse[]> {
	// 1. Get company ID
	const company = await db
		.selectFrom('companies')
		.select('id')
		.where('ticker', '=', ticker.toUpperCase())
		.executeTakeFirst();

	if (!company) return [];

	// 2. Get filings ordered by period_of_report ASC
	const filings = await db
		.selectFrom('filings')
		.selectAll()
		.where('company_id', '=', company.id)
		.orderBy('period_of_report', 'asc')
		.limit(limit)
		.execute();

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
	const gcByDocId = new Map<string, Array<{
		id: string;
		content_hash: string | null;
		short_hash: string | null;
		description: string | null;
		document_type: string | null;
		form_type: string | null;
		content_stage: string | null;
		summary: string | null;
		created_at: string;
	}>>();

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

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
