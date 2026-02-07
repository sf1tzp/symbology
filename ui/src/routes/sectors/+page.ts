import type { PageLoad } from './$types';
import { getCompanyGroups } from '$lib/api';

export const load: PageLoad = async () => {
	try {
		const groups = await getCompanyGroups('sector', 50);

		return {
			groups
		};
	} catch (error) {
		console.error('Failed to load sectors:', error);
		return {
			groups: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
