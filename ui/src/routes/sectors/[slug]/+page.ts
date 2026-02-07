import type { PageLoad } from './$types';
import { getCompanyGroupBySlug, getGroupAnalysis } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
	const { slug } = params;

	try {
		const [group, analyses] = await Promise.all([
			getCompanyGroupBySlug(slug),
			getGroupAnalysis(slug, 5)
		]);

		return {
			slug,
			group,
			analyses
		};
	} catch (error) {
		console.error(`Failed to load sector ${slug}:`, error);
		return {
			slug,
			group: null,
			analyses: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
