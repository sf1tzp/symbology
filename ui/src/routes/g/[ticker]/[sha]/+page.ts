import type { PageLoad } from './$types';
import {
	getCompanyByTicker,
	getGeneratedContentByTickerAndHash,
	getModelConfigById,
	getDocumentById,
	getGeneratedContentById
} from '$lib/api';

export const load: PageLoad = async ({ params, fetch }) => {
	const { ticker, sha } = params;

	try {
		// Try to fetch real data from the API
		const [content, company] = await Promise.all([
			getGeneratedContentByTickerAndHash(ticker, sha),
			getCompanyByTicker(ticker)
		]);

		// If both API calls succeed, use real data
		if (content && company) {
			// Fetch model config if available
			let modelConfig = null;
			if (content.model_config_id) {
				try {
					modelConfig = await getModelConfigById(content.model_config_id);
				} catch (error) {
					console.warn('Failed to fetch model config:', error);
				}
			}

			// Fetch source documents if available
			let sources: any[] = [];

			// Fetch source documents
			if (content.source_document_ids && content.source_document_ids.length > 0) {
				try {
					const documentPromises = content.source_document_ids.map((docId: string) =>
						getDocumentById(docId).catch((error) => {
							console.warn(`Failed to fetch document ${docId}:`, error);
							return null;
						})
					);
					const documents = await Promise.all(documentPromises);
					// Add source type to distinguish documents from generated content
					const documentSources = documents
						.filter((doc) => doc !== null)
						.map((doc) => ({
							...doc,
							source_type: 'document'
						}));
					sources.push(...documentSources);
				} catch (error) {
					console.warn('Failed to fetch source documents:', error);
				}
			}

			// Fetch source generated content
			if (content.source_content_ids && content.source_content_ids.length > 0) {
				try {
					const contentPromises = content.source_content_ids.map((contentId: string) =>
						getGeneratedContentById(contentId).catch((error) => {
							console.warn(`Failed to fetch generated content ${contentId}:`, error);
							return null;
						})
					);
					const contents = await Promise.all(contentPromises);
					// Add source type to distinguish generated content from documents
					const contentSources = contents
						.filter((content) => content !== null)
						.map((content) => ({
							...content,
							source_type: 'generated_content'
						}));
					sources.push(...contentSources);
				} catch (error) {
					console.warn('Failed to fetch source generated content:', error);
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
		}
	} catch (error) {
		console.warn('API call failed:', error);
	}

	// If we get here, either the API calls failed or returned null
	// Instead of falling back to mock data, throw an error to show a proper error page
	throw new Error(`Generated content not found for ticker '${ticker}' and hash '${sha}'`);
};
