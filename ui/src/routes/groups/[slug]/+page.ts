import type { PageLoad } from './$types';
import { getCompanyGroupBySlug, getGroupAnalysis, getGroupFrontpageSummary } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
	const { slug } = params;

	try {
		const [group, analyses, frontpageSummary] = await Promise.all([
			getCompanyGroupBySlug(slug),
			getGroupAnalysis(slug, 5),
			getGroupFrontpageSummary(slug)
		]);

		return {
			slug,
			group,
			analyses,
			frontpageSummary
		};
	} catch (error) {
		console.error(`Failed to load group ${slug}:`, error);
		return {
			slug,
			group: null,
			analyses: [],
			frontpageSummary: null,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
