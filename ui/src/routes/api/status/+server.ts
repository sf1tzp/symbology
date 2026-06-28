import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { collectStatus, STAT_WINDOW } from '$lib/server/db/status';
import { viewerIsSupporter } from '$lib/server/gating';

export const GET: RequestHandler = async ({ locals }) => {
	// Mirror the status page's supporter gate so the polling feed can't leak it.
	if (!(await viewerIsSupporter(locals.user))) {
		return json({ error: 'Supporter status required' }, { status: 403 });
	}
	try {
		const snapshot = await collectStatus(STAT_WINDOW);
		return json(snapshot);
	} catch (error) {
		console.error('Failed to load status data:', error);
		return json({ error: 'Failed to load status data' }, { status: 500 });
	}
};
