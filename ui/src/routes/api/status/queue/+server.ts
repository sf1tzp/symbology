import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { collectQueueStatus, parseJobStatusFilter, STAT_WINDOW } from '$lib/server/db/status';
import { viewerIsSupporter } from '$lib/server/gating';

// The fast-poll endpoint: just the queue/jobs/workers slice, so the status page
// can refresh those every ~15s without re-running the heavy snapshot aggregations
// (which stay on the slower /api/status poll).
//
// An optional `?status=` param scopes the recent-jobs list to one status (failed
// / backoff / completed / …) — a deliberate filtered lookup that reaches past the
// default 100-row tail. Queue counts and workers stay global regardless.
export const GET: RequestHandler = async ({ url, locals }) => {
	// Mirror the status page's supporter gate so the polling feed can't leak it.
	if (!(await viewerIsSupporter(locals.user))) {
		return json({ error: 'Supporter status required' }, { status: 403 });
	}
	try {
		const status = parseJobStatusFilter(url.searchParams.get('status'));
		return json(await collectQueueStatus(STAT_WINDOW, status));
	} catch (error) {
		console.error('Failed to load queue status:', error);
		return json({ error: 'Failed to load queue status' }, { status: 500 });
	}
};
