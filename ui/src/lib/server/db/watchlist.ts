import { db } from '../db';

export interface WatchlistItem {
	company_id: string;
	ticker: string;
	name: string;
	display_name: string | null;
	sic_description: string | null;
	added_at: string;
}

/** Companies a user is watching, most-recently-added first. */
export async function getWatchlist(userId: string): Promise<WatchlistItem[]> {
	const rows = await db
		.selectFrom('watchlist as w')
		.innerJoin('companies as c', 'c.id', 'w.company_id')
		.select([
			'c.id as company_id',
			'c.ticker',
			'c.name',
			'c.display_name',
			'c.sic_description',
			'w.created_at as added_at'
		])
		.where('w.user_id', '=', userId)
		.orderBy('w.created_at', 'desc')
		.execute();

	return rows.map((r) => ({
		company_id: r.company_id,
		ticker: r.ticker,
		name: r.name,
		display_name: r.display_name,
		sic_description: r.sic_description,
		added_at: r.added_at instanceof Date ? r.added_at.toISOString() : String(r.added_at)
	}));
}

/** Star a company. Idempotent via the (user_id, company_id) unique constraint. */
export async function addToWatchlist(userId: string, companyId: string): Promise<void> {
	await db
		.insertInto('watchlist')
		.values({ user_id: userId, company_id: companyId })
		.onConflict((oc) => oc.columns(['user_id', 'company_id']).doNothing())
		.execute();
}

/** Unstar a company. No-op if it wasn't on the list. */
export async function removeFromWatchlist(userId: string, companyId: string): Promise<void> {
	await db
		.deleteFrom('watchlist')
		.where('user_id', '=', userId)
		.where('company_id', '=', companyId)
		.execute();
}

/** True if the user is already watching the given company. */
export async function isWatching(userId: string, companyId: string): Promise<boolean> {
	const row = await db
		.selectFrom('watchlist')
		.select('id')
		.where('user_id', '=', userId)
		.where('company_id', '=', companyId)
		.executeTakeFirst();
	return !!row;
}
