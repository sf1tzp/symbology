import type { PageServerLoad } from './$types';
import { collectStatus, STAT_WINDOW } from '$lib/server/db/status';

export const load: PageServerLoad = async () => {
	try {
		const snapshot = await collectStatus(STAT_WINDOW);
		return { stat_window: STAT_WINDOW, ...snapshot };
	} catch (error) {
		console.error('Failed to load status data:', error);
		return {
			stat_window: null,
			hero: null,
			ingestionDays: [],
			recentFilings: [],
			contentBreakdown: [],
			modelBreakdown: [],
			contentThroughput: [],
			contentLog: [],
			queueStats: null,
			queueDepth: [],
			recentJobs: [],
			workers: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
