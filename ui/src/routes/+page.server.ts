import type { PageServerLoad } from './$types';
import { getFeaturedCompanyIntros } from '$lib/server/db/page-content';

export const load: PageServerLoad = async ({ fetch }) => {
	const [statsRes, featured] = await Promise.all([
		fetch('/api/stats'),
		getFeaturedCompanyIntros(3)
	]);

	const stats = statsRes.ok ? await statsRes.json() : null;

	return { stats, featured };
};
