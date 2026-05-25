import { db } from '../db';
import type { DocumentResponse } from '$lib/api-types';

export async function getDocumentByAccessionAndHash(
	accessionNumber: string,
	contentHash: string
): Promise<DocumentResponse | null> {
	// Find the filing by accession number
	const filing = await db
		.selectFrom('filings')
		.selectAll()
		.where('accession_number', '=', accessionNumber)
		.executeTakeFirst();

	if (!filing) return null;

	// Find the document by content_hash prefix match within that filing
	const doc = await db
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
		.where('documents.content_hash', 'like', `${contentHash}%`)
		.executeTakeFirst();

	if (!doc) return null;

	return {
		id: doc.id,
		filing_id: doc.filing_id,
		company_ticker: doc.company_ticker,
		title: doc.title,
		document_type: doc.document_type ?? 'unknown',
		content: doc.content,
		content_hash: doc.content_hash,
		short_hash: doc.content_hash?.slice(0, 12) ?? null,
		filing: {
			id: filing.id,
			company_id: filing.company_id,
			accession_number: filing.accession_number,
			form: filing.form,
			filing_date: toDateString(filing.filing_date),
			url: filing.url,
			period_of_report: filing.period_of_report ? toDateString(filing.period_of_report) : null
		}
	};
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
