import type { PageServerLoad } from './$types';
import type { DocumentResponse, GeneratedContentResponse } from '$lib/api-types';
import { error } from '@sveltejs/kit';
import {
	getGeneratedContentByHash,
	getGeneratedContentById,
	getModelConfigById,
	getDocumentById,
	getPromptById,
	getTopicDiffViewByContentId,
	resolveContentScope
} from '$lib/server/db/generated-content';

export const load: PageServerLoad = async ({ params }) => {
	const { sha } = params;

	const content = await getGeneratedContentByHash(sha);

	if (!content) {
		error(404, `Synthesis not found for hash '${sha}'`);
	}

	// Resolve the subject scope (company / group / …) from the content itself,
	// plus model config + prompts (any may be absent), in parallel.
	const [scope, modelConfig, systemPrompt, userPrompt, diffView] = await Promise.all([
		resolveContentScope(content),
		content.model_config_id ? getModelConfigById(content.model_config_id) : null,
		content.system_prompt_id ? getPromptById(content.system_prompt_id) : null,
		content.user_prompt_id ? getPromptById(content.user_prompt_id) : null,
		// Topic-diff summaries carry their sources as the section diff's two halves
		// rather than association rows; reconstruct them (raw ops + filing refs) so
		// the page can render them through the shared side-by-side DiffView.
		content.content_stage === 'topic_diff_summary'
			? getTopicDiffViewByContentId(content.id)
			: Promise.resolve(null)
	]);

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
			sources,
			systemPrompt,
			userPrompt,
			diffView
		},
		scope,
		sha
	};
};
