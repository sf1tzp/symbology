import type { PageServerLoad } from './$types';
import { getFeaturedCompanyIntros } from '$lib/server/db/page-content';
import { getFeaturedLandingDiff } from '$lib/server/db/diffs';

export const load: PageServerLoad = async ({ fetch }) => {
	const [statsRes, featured, featuredDiff] = await Promise.all([
		fetch('/api/stats'),
		getFeaturedCompanyIntros(3),
		getFeaturedLandingDiff()
	]);

	const stats = statsRes.ok ? await statsRes.json() : null;

	return { stats, featured, featuredDiff };
};
