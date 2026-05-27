import type { PageServerLoad } from './$types';
import {
	getHeroStats,
	getFilingIngestionByDay,
	getRecentFilings,
	getContentBreakdown,
	getContentThroughput,
	getContentLog,
	getJobQueueStats,
	getJobQueueDepth,
	getActiveJobs,
	getWorkerSummary
} from '$lib/server/db/status';

export const load: PageServerLoad = async () => {
	try {
		const [
			hero,
			ingestionDays,
			recentFilings,
			contentBreakdown,
			contentThroughput,
			contentLog,
			queueStats,
			queueDepth,
			activeJobs,
			workers
		] = await Promise.all([
			getHeroStats(),
			getFilingIngestionByDay(14),
			getRecentFilings(8),
			getContentBreakdown(),
			getContentThroughput(14),
			getContentLog(9),
			getJobQueueStats(),
			getJobQueueDepth(24),
			getActiveJobs(10),
			getWorkerSummary()
		]);

		return {
			hero,
			ingestionDays,
			recentFilings,
			contentBreakdown,
			contentThroughput,
			contentLog,
			queueStats,
			queueDepth,
			activeJobs,
			workers
		};
	} catch (error) {
		console.error('Failed to load status data:', error);
		return {
			hero: null,
			ingestionDays: [],
			recentFilings: [],
			contentBreakdown: [],
			contentThroughput: [],
			contentLog: [],
			queueStats: null,
			queueDepth: [],
			activeJobs: [],
			workers: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
