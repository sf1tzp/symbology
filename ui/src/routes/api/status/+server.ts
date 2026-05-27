import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
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

export const GET: RequestHandler = async () => {
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

		return json({
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
		});
	} catch (error) {
		console.error('Failed to load status data:', error);
		return json({ error: 'Failed to load status data' }, { status: 500 });
	}
};
