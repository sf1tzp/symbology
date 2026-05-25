import type { PageServerLoad } from './$types';
import { getCompanyGroupBySlug, getGroupAnalysis, getGroupFrontpageSummary } from '$lib/server/db/groups';

export const load: PageServerLoad = async ({ params }) => {
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
