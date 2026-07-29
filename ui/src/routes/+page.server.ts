import type { PageServerLoad } from './$types';
import { getLandingShowcase } from '$lib/server/db/landing';

export const load: PageServerLoad = async ({ fetch }) => {
	const [statsRes, showcase] = await Promise.all([fetch('/api/stats'), getLandingShowcase(3)]);

	const stats = statsRes.ok ? await statsRes.json() : null;

	return { stats, showcase };
};
