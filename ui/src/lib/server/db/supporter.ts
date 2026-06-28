import { db } from '../db';
import { SUPPORT_CAP_ISO, earnedBadges, type AmountBadge } from '$lib/supporter-plans';

const DAY_MS = 86_400_000;

/** A user's current supporter standing, derived from their grant ledger. */
export interface SupporterStatus {
	/** True while the supporter window is still open. */
	active: boolean;
	/** End of the current window (max expires_at), or null if never supported. */
	expiresAt: string | null;
	/** Whole days remaining (ceil), 0 when lapsed. */
	daysLeft: number;
	/** Total ever contributed, in cents. */
	totalCents: number;
	/** First grant timestamp, or null. */
	since: string | null;
	/** plan_type of the most recent grant ('one' | 'duration'), or null. */
	latestPlan: string | null;
	/** Distinct easter-egg badges earned from pledge amounts (de-duped). */
	badges: AmountBadge[];
}

const toIso = (v: unknown): string => (v instanceof Date ? v.toISOString() : String(v));

/**
 * Full supporter status for a user, computed from every grant they hold.
 * Grants stack, so the active window is simply the furthest `expires_at`.
 */
export async function getSupporterStatus(userId: string): Promise<SupporterStatus> {
	const rows = await db
		.selectFrom('supporter_grants')
		.select(['amount_cents', 'expires_at', 'granted_at', 'plan_type'])
		.where('user_id', '=', userId)
		.orderBy('expires_at', 'desc')
		.execute();

	if (rows.length === 0) {
		return {
			active: false,
			expiresAt: null,
			daysLeft: 0,
			totalCents: 0,
			since: null,
			latestPlan: null,
			badges: []
		};
	}

	const now = Date.now();
	const maxExpires = new Date(toIso(rows[0].expires_at)).getTime();
	const active = maxExpires > now;
	const totalCents = rows.reduce((sum, r) => sum + r.amount_cents, 0);
	const since = rows.reduce<string>((min, r) => {
		const g = toIso(r.granted_at);
		return min === '' || g < min ? g : min;
	}, '');

	return {
		active,
		expiresAt: toIso(rows[0].expires_at),
		daysLeft: active ? Math.ceil((maxExpires - now) / DAY_MS) : 0,
		totalCents,
		since: since || null,
		latestPlan: rows[0].plan_type,
		// Badges are earned by the dollar amount of each pledge (== days for the
		// $1/day plan; $20 for the one-time, which earns nothing).
		badges: earnedBadges(rows.map((r) => r.amount_cents / 100))
	};
}

/** Cheap boolean check — true if the user has an open supporter window. */
export async function isSupporter(userId: string): Promise<boolean> {
	const row = await db
		.selectFrom('supporter_grants')
		.select('id')
		.where('user_id', '=', userId)
		.where('expires_at', '>', new Date())
		.limit(1)
		.executeTakeFirst();
	return !!row;
}

export interface GrantInput {
	userId: string;
	days: number;
	amountCents: number;
	planType: string;
	provider: string;
	/** Idempotency key — the Stripe PaymentIntent/session id. */
	providerTxnId: string;
}

/**
 * Record a completed purchase. Idempotent on `providerTxnId` (the Stripe
 * webhook may fire more than once). Days stack: the new window starts from
 * whichever is later — now, or the user's current furthest expiry — so a
 * top-up never shortens an existing window.
 */
export async function grantSupporter(input: GrantInput): Promise<void> {
	// Idempotency: bail if we've already recorded this transaction.
	const existing = await db
		.selectFrom('supporter_grants')
		.select('id')
		.where('provider_txn_id', '=', input.providerTxnId)
		.executeTakeFirst();
	if (existing) return;

	// Stack onto the current furthest expiry (or now, whichever is later).
	const current = await db
		.selectFrom('supporter_grants')
		.select('expires_at')
		.where('user_id', '=', input.userId)
		.orderBy('expires_at', 'desc')
		.limit(1)
		.executeTakeFirst();

	const now = Date.now();
	const base = current ? Math.max(now, new Date(toIso(current.expires_at)).getTime()) : now;
	// Stack the new days on, but never let a window extend past the policy cap.
	// Checkout already blocks over-cap purchases; this is the last-line guard for
	// the race where two grants land close together.
	const expiresAt = new Date(Math.min(base + input.days * DAY_MS, Date.parse(SUPPORT_CAP_ISO)));

	await db
		.insertInto('supporter_grants')
		.values({
			user_id: input.userId,
			amount_cents: input.amountCents,
			days: input.days,
			expires_at: expiresAt,
			provider: input.provider,
			provider_txn_id: input.providerTxnId,
			plan_type: input.planType
		})
		// Guards the race where two webhook deliveries land concurrently.
		.onConflict((oc) => oc.column('provider_txn_id').doNothing())
		.execute();
}
