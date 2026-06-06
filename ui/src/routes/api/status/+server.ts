import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { collectStatus, STAT_WINDOW } from '$lib/server/db/status';

export const GET: RequestHandler = async () => {
	try {
		const snapshot = await collectStatus(STAT_WINDOW);
		return json(snapshot);
	} catch (error) {
		console.error('Failed to load status data:', error);
		return json({ error: 'Failed to load status data' }, { status: 500 });
	}
};
