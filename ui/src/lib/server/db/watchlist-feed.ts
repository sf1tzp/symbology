import { sql } from 'kysely';
import { db } from '../db';
import { getTopChangeByFilings } from './diffs';

/**
 * The watchlist "what changed" feed: one item per watched company, anchored to
 * that company's single most recent 10-K/10-Q. When that filing has a summarised
 * material change we show it as a highlight (deep-linking to the filing's diff
 * section); otherwise we show a plain "filed a 10-Q" row. UI-side, read-time.
 */

const MS_PER_DAY = 86_400_000;

export type FeedItemKind = 'filing' | 'change';

export interface FeedItem {
	kind: FeedItemKind;
	/** section_diff id (change) or filing id (filing) — stable {#each} key. */
	id: string;
	companyId: string;
	ticker: string;
	companyName: string;
	/** The anchoring filing's form (10-K / 10-Q). */
	form: string;
	/** ISO filing_date of the anchoring filing. */
	occurredAt: string;
	href: string;
	// change-only:
	summary?: string | null;
	documentType?: string;
	changeKind?: string;
}

export interface WatchlistFeed {
	items: FeedItem[];
	stats: { newFilings: number; materialChanges: number; sinceDays: number };
}

function toIsoDate(val: unknown): string {
	const s = val instanceof Date ? val.toISOString() : String(val);
	return s.split('T')[0];
}

interface LatestFilingRow {
	id: string;
	company_id: string;
	form: string;
	accession_number: string;
	filing_date: unknown;
	ticker: string;
	name: string;
	display_name: string | null;
}

/**
 * Build the feed for a set of watched companies. One item per company keyed on
 * its latest 10-K/10-Q; `sinceDays` (default 30) defines the "new filings" stat
 * window; `limit` (default 12) caps the rendered list (newest first). Empty
 * input → empty feed.
 */
export async function getWatchlistFeed(
	companyIds: string[],
	opts: { sinceDays?: number; limit?: number; today?: Date } = {}
): Promise<WatchlistFeed> {
	const sinceDays = opts.sinceDays ?? 30;
	const limit = opts.limit ?? 12;
	if (companyIds.length === 0) {
		return { items: [], stats: { newFilings: 0, materialChanges: 0, sinceDays } };
	}
	const today = opts.today ?? new Date();
	const since = new Date(today.getTime() - sinceDays * MS_PER_DAY);

	// Each company's single most recent periodic filing, plus a count of filings
	// across the watchlist in the "new filings" window.
	const [latest, newFilingsRow] = await Promise.all([
		db
			.selectFrom('filings as f')
			.innerJoin('companies as c', 'c.id', 'f.company_id')
			.select([
				'f.id',
				'f.company_id',
				'f.form',
				'f.accession_number',
				'f.filing_date',
				'c.ticker',
				'c.name',
				'c.display_name'
			])
			.where('f.company_id', 'in', companyIds)
			.where('f.form', 'in', ['10-K', '10-Q'])
			.distinctOn('f.company_id')
			.orderBy('f.company_id')
			.orderBy('f.filing_date', 'desc')
			.execute() as Promise<LatestFilingRow[]>,
		db
			.selectFrom('filings')
			.select(sql<number>`count(*)::int`.as('n'))
			.where('company_id', 'in', companyIds)
			.where('form', 'in', ['10-K', '10-Q'])
			.where('filing_date', '>=', since)
			.executeTakeFirst()
	]);

	// The single best summarised change per latest filing (absent when none).
	const highlights = await getTopChangeByFilings(latest.map((f) => f.id));

	const items: FeedItem[] = latest.map((f) => {
		const occurredAt = toIsoDate(f.filing_date);
		const companyName = f.display_name ?? f.name;
		const hl = highlights.get(f.id);
		if (hl) {
			return {
				kind: 'change',
				id: hl.sectionDiffId,
				companyId: f.company_id,
				ticker: f.ticker,
				companyName,
				form: f.form,
				occurredAt,
				href: `/f/${f.accession_number}#diff-${hl.sectionDiffId}`,
				summary: hl.summary,
				documentType: hl.documentType,
				changeKind: hl.changeKind
			};
		}
		return {
			kind: 'filing',
			id: f.id,
			companyId: f.company_id,
			ticker: f.ticker,
			companyName,
			form: f.form,
			occurredAt,
			href: `/f/${f.accession_number}`
		};
	});

	// Newest filing first.
	items.sort((a, b) => (a.occurredAt < b.occurredAt ? 1 : a.occurredAt > b.occurredAt ? -1 : 0));

	return {
		items: items.slice(0, limit),
		stats: {
			newFilings: Number(newFilingsRow?.n ?? 0),
			materialChanges: items.filter((i) => i.kind === 'change').length,
			sinceDays
		}
	};
}
