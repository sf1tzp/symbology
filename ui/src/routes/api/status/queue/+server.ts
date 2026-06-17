import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { collectQueueStatus } from '$lib/server/db/status';

// The fast-poll endpoint: just the queue/jobs/workers slice, so the status page
// can refresh those every ~15s without re-running the heavy snapshot aggregations
// (which stay on the slower /api/status poll).
export const GET: RequestHandler = async () => {
	try {
		return json(await collectQueueStatus());
	} catch (error) {
		console.error('Failed to load queue status:', error);
		return json({ error: 'Failed to load queue status' }, { status: 500 });
	}
};
