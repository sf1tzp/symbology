import type { PageServerLoad } from './$types';
import {
	getCompanyGroupBySlug,
	getGroupAnalysis,
	getGroupFrontpageSummary
} from '$lib/server/db/groups';
import { getModelConfigById } from '$lib/server/db/generated-content';

export const load: PageServerLoad = async ({ params }) => {
	const { slug } = params;

	try {
		const [group, analyses, frontpageSummary] = await Promise.all([
			getCompanyGroupBySlug(slug),
			getGroupAnalysis(slug, 5),
			getGroupFrontpageSummary(slug)
		]);

		// Fetch model config for the most recent analysis
		const latestAnalysis = analyses.length > 0 ? analyses[0] : null;
		const modelConfig = latestAnalysis?.model_config_id
			? await getModelConfigById(latestAnalysis.model_config_id)
			: null;

		return {
			slug,
			group,
			analyses,
			frontpageSummary,
			modelConfig
		};
	} catch (error) {
		console.error(`Failed to load group ${slug}:`, error);
		return {
			slug,
			group: null,
			analyses: [],
			frontpageSummary: null,
			modelConfig: null,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
