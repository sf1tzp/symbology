import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { collectStatus, STAT_WINDOW } from '$lib/server/db/status';
import { viewerIsSupporter } from '$lib/server/gating';

export const load: PageServerLoad = async ({ locals }) => {
	// The operations dashboard is a supporter perk; non-supporters (and signed-out
	// visitors) are bounced to the support pitch. While the supporter program is
	// gated off pre-launch, `viewerIsSupporter` returns true for everyone, so this
	// is effectively public.
	if (!(await viewerIsSupporter(locals.user))) {
		redirect(302, '/support');
	}

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
