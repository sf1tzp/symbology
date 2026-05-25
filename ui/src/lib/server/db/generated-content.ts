import { db } from '../db';
import type { GeneratedContentResponse, GeneratedContentSummaryResponse } from '$lib/api-types';

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

async function toGeneratedContentResponse(row: any): Promise<GeneratedContentResponse> {
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

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}
