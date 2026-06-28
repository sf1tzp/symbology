import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { addToWatchlist, getWatchlist, removeFromWatchlist } from '$lib/server/db/watchlist';
import { getSupporterStatus } from '$lib/server/db/supporter';
import { getWatchlistFeed } from '$lib/server/db/watchlist-feed';
import { getUpcomingFilings } from '$lib/server/db/predictions';
import { getLatestChangeCardsForCompanies } from '$lib/server/db/diffs';
import { getFinancialComparison } from '$lib/server/db/financials';
import { pickHeadlineStats } from '$lib/utils/financials';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		redirect(302, `/login?returnTo=${encodeURIComponent(url.pathname)}`);
	}
	const watching = await getWatchlist(locals.user.id);
	const companyIds = watching.map((w) => w.company_id);

	const [supporter, feed, upcoming, changeCards, yoyEntries] = await Promise.all([
		getSupporterStatus(locals.user.id),
		getWatchlistFeed(companyIds, { sinceDays: 30, limit: 12 }),
		getUpcomingFilings(companyIds), // one prediction per company; sliced below
		getLatestChangeCardsForCompanies(companyIds), // for per-company change counts
		// Headline YoY metric per company (reuses the company-page "data row" code).
		Promise.all(
			watching.map(async (w) => {
				const fin = await getFinancialComparison(w.ticker, undefined, 2, '10-K');
				const stat = pickHeadlineStats(fin, 1)[0] ?? null;
				return [
					w.company_id,
					stat ? { label: stat.label, percent: stat.change?.percent ?? null } : null
				] as const;
			})
		)
	]);

	// Index the per-company derivations for the "Watching" cards.
	const nextByCompany = new Map(upcoming.map((u) => [u.companyId, u]));
	const yoyByCompany = new Map(yoyEntries);
	const changeCountByCompany = new Map<string, number>();
	for (const c of changeCards) {
		changeCountByCompany.set(c.companyId, (changeCountByCompany.get(c.companyId) ?? 0) + 1);
	}

	const watchingEnriched = watching.map((w) => ({
		...w,
		nextFiling: nextByCompany.get(w.company_id) ?? null,
		changeCount: changeCountByCompany.get(w.company_id) ?? 0,
		yoy: yoyByCompany.get(w.company_id) ?? null
	}));

	// Watched companies we couldn't estimate a next filing for (no 10-K/10-Q
	// history yet) — surfaced as muted rows so every company appears.
	const calendarMissing = watching
		.filter((w) => !nextByCompany.has(w.company_id))
		.map((w) => ({
			companyId: w.company_id,
			ticker: w.ticker,
			companyName: w.display_name ?? w.name
		}));

	return {
		watching: watchingEnriched,
		feed,
		// Every watched company's next estimated filing (no date-window cap), soonest first.
		calendar: upcoming,
		calendarMissing,
		badges: supporter.badges,
		firstName: locals.user.name.trim().split(/\s+/)[0] || locals.user.name
	};
};

export const actions: Actions = {
	add: async ({ request, locals }) => {
		if (!locals.user) return fail(401, { message: 'Not signed in' });
		const data = await request.formData();
		const companyId = String(data.get('companyId') ?? '');
		if (!companyId) return fail(400, { message: 'Missing company' });
		await addToWatchlist(locals.user.id, companyId);
		return { success: true };
	},
	remove: async ({ request, locals }) => {
		if (!locals.user) return fail(401, { message: 'Not signed in' });
		const data = await request.formData();
		const companyId = String(data.get('companyId') ?? '');
		if (!companyId) return fail(400, { message: 'Missing company' });
		await removeFromWatchlist(locals.user.id, companyId);
		return { success: true };
	}
};
