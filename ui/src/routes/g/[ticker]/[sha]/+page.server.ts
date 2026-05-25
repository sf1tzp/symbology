import type { PageServerLoad } from './$types';
import type { DocumentResponse, GeneratedContentResponse } from '$lib/api-types';
import { error } from '@sveltejs/kit';
import { getCompanyByTicker } from '$lib/server/db/companies';
import {
	getGeneratedContentByTickerAndHash,
	getGeneratedContentById,
	getModelConfigById,
	getDocumentById
} from '$lib/server/db/generated-content';

export const load: PageServerLoad = async ({ params }) => {
	const { ticker, sha } = params;

	const [content, company] = await Promise.all([
		getGeneratedContentByTickerAndHash(ticker, sha),
		getCompanyByTicker(ticker)
	]);

	if (!content || !company) {
		error(404, `Generated content not found for ticker '${ticker}' and hash '${sha}'`);
	}

	// Fetch model config if available
	let modelConfig = null;
	if (content.model_config_id) {
		modelConfig = await getModelConfigById(content.model_config_id);
	}

	// Fetch source documents and content
	type SourceItem =
		| (DocumentResponse & { source_type: string })
		| (GeneratedContentResponse & { source_type: string });
	const sources: SourceItem[] = [];

	if (content.source_document_ids && content.source_document_ids.length > 0) {
		const documents = await Promise.all(
			content.source_document_ids.map((docId) => getDocumentById(docId))
		);
		for (const doc of documents) {
			if (doc) sources.push({ ...doc, source_type: 'document' });
		}
	}

	if (content.source_content_ids && content.source_content_ids.length > 0) {
		const contents = await Promise.all(
			content.source_content_ids.map((id) => getGeneratedContentById(id))
		);
		for (const c of contents) {
			if (c) sources.push({ ...c, source_type: 'generated_content' });
		}
	}

	return {
		content: {
			...content,
			modelConfig,
			sources
		},
		company,
		ticker,
		sha
	};
};
