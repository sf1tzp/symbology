import { db } from '../db';
import type { Selectable } from 'kysely';
import type {
	DocumentResponse,
	GeneratedContentResponse,
	GeneratedContentSummaryResponse,
	ModelConfigResponse
} from '$lib/api-types';
import type { GeneratedContent } from './types';

export async function getAggregateSummariesByTicker(
	ticker: string,
	limit: number = 5
): Promise<GeneratedContentResponse[]> {
	const rows = await db
		.selectFrom('generated_content as gc')
		.innerJoin('companies as c', 'c.id', 'gc.company_id')
		.selectAll('gc')
		.where('c.ticker', '=', ticker.toUpperCase())
		.where((eb) =>
			eb.or([
				eb('gc.content_stage', '=', 'aggregate_summary'),
				eb('gc.description', 'like', '%aggregate_summary%')
			])
		)
		.orderBy('gc.created_at', 'desc')
		.limit(limit)
		.execute();

	return Promise.all(rows.map((row) => toGeneratedContentResponse(row)));
}

export async function getAllGeneratedContentByTicker(
	ticker: string,
	limit: number = 100
): Promise<GeneratedContentSummaryResponse[]> {
	const rows = await db
		.selectFrom('generated_content as gc')
		.innerJoin('companies as c', 'c.id', 'gc.company_id')
		.select([
			'gc.id',
			'gc.content_hash',
			'gc.description',
			'gc.document_type',
			'gc.form_type',
			'gc.content_stage',
			'gc.summary',
			'gc.created_at'
		])
		.where('c.ticker', '=', ticker.toUpperCase())
		.orderBy('gc.created_at', 'desc')
		.limit(limit)
		.execute();

	return rows.map((row) => ({
		id: row.id,
		content_hash: row.content_hash,
		short_hash: row.content_hash?.slice(0, 12) ?? null,
		description: row.description,
		document_type: row.document_type,
		form_type: row.form_type,
		content_stage: row.content_stage,
		summary: row.summary,
		created_at: toISOString(row.created_at)
	}));
}

async function toGeneratedContentResponse(
	row: Selectable<GeneratedContent>
): Promise<GeneratedContentResponse> {
	const [docIds, contentIds] = await Promise.all([
		db
			.selectFrom('generated_content_document_association')
			.select('document_id')
			.where('generated_content_id', '=', row.id)
			.execute(),
		db
			.selectFrom('generated_content_source_association')
			.select('source_content_id')
			.where('parent_content_id', '=', row.id)
			.execute()
	]);

	return {
		id: row.id,
		content_hash: row.content_hash,
		short_hash: row.content_hash?.slice(0, 12) ?? null,
		company_id: row.company_id,
		description: row.description,
		document_type: row.document_type,
		form_type: row.form_type,
		source_type: row.source_type,
		created_at: toISOString(row.created_at),
		total_duration: row.total_duration,
		input_tokens: row.input_tokens,
		output_tokens: row.output_tokens,
		warning: row.warning,
		content: row.content,
		summary: row.summary,
		model_config_id: row.model_config_id,
		system_prompt_id: row.system_prompt_id,
		user_prompt_id: row.user_prompt_id,
		source_document_ids: docIds.map((r) => r.document_id),
		source_content_ids: contentIds.map((r) => r.source_content_id)
	};
}

export async function getGeneratedContentByTickerAndHash(
	ticker: string,
	hash: string
): Promise<GeneratedContentResponse | null> {
	const row = await db
		.selectFrom('generated_content as gc')
		.innerJoin('companies as c', 'c.id', 'gc.company_id')
		.selectAll('gc')
		.where('c.ticker', '=', ticker.toUpperCase())
		.where('gc.content_hash', 'like', `${hash}%`)
		.executeTakeFirst();

	if (!row) return null;

	return toGeneratedContentResponse(row);
}

export async function getGeneratedContentById(
	id: string
): Promise<GeneratedContentResponse | null> {
	const row = await db
		.selectFrom('generated_content')
		.selectAll()
		.where('id', '=', id)
		.executeTakeFirst();

	if (!row) return null;

	return toGeneratedContentResponse(row);
}

export async function getModelConfigById(id: string): Promise<ModelConfigResponse | null> {
	const row = await db
		.selectFrom('model_configs')
		.selectAll()
		.where('id', '=', id)
		.executeTakeFirst();

	if (!row) return null;

	const options = row.options_json ? JSON.parse(row.options_json) : null;

	return {
		id: row.id,
		model: row.model,
		created_at: toISOString(row.created_at),
		options,
		max_tokens: options?.max_tokens ?? null,
		temperature: options?.temperature ?? null,
		top_k: options?.top_k ?? null,
		top_p: options?.top_p ?? null
	};
}

export async function getDocumentById(id: string): Promise<DocumentResponse | null> {
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
		.where('documents.id', '=', id)
		.executeTakeFirst();

	if (!doc) return null;

	// Fetch filing info if available
	let filing = null;
	if (doc.filing_id) {
		const f = await db
			.selectFrom('filings')
			.selectAll()
			.where('id', '=', doc.filing_id)
			.executeTakeFirst();
		if (f) {
			filing = {
				id: f.id,
				company_id: f.company_id,
				accession_number: f.accession_number,
				form: f.form,
				filing_date: toDateString(f.filing_date),
				url: f.url,
				period_of_report: f.period_of_report ? toDateString(f.period_of_report) : null
			};
		}
	}

	return {
		id: doc.id,
		filing_id: doc.filing_id,
		company_ticker: doc.company_ticker,
		title: doc.title,
		document_type: doc.document_type ?? 'unknown',
		content: doc.content,
		content_hash: doc.content_hash,
		short_hash: doc.content_hash?.slice(0, 12) ?? null,
		filing
	};
}

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
