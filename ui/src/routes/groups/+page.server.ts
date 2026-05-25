import type { PageServerLoad } from './$types';
import { getCompanyGroups } from '$lib/server/db/groups';

export const load: PageServerLoad = async () => {
	try {
		const groups = await getCompanyGroups(50);
		return { groups };
	} catch (error) {
		console.error('Failed to load groups:', error);
		return {
			groups: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
