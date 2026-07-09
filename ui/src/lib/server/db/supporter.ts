import { db } from '../db';
import {
	SUPPORT_CAP_ISO,
	MAXXING_BADGE,
	daysAllowedBeforeCap,
	earnedBadges,
	type AmountBadge
} from '$lib/supporter-plans';

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
	/** Number of contributions (grants) on record. */
	grantCount: number;
	/** First grant timestamp, or null. */
	since: string | null;
	/** plan_type of the most recent grant ('one' | 'duration'), or null. */
	latestPlan: string | null;
	/** Distinct easter-egg badges earned from pledge amounts (de-duped). */
	badges: AmountBadge[];
}

/** One purchase from the supporter ledger, newest-first for the billing page. */
export interface SupporterGrant {
	id: string;
	amountCents: number;
	days: number;
	grantedAt: string;
	expiresAt: string;
	planType: string;
	provider: string;
	providerTxnId: string;
}

const toIso = (v: unknown): string => (v instanceof Date ? v.toISOString() : String(v));

/**
 * Every grant a user holds, newest first — the raw ledger behind the billing
 * history page. (`getSupporterStatus` is the rolled-up view for the account card.)
 */
export async function getSupporterGrants(userId: string): Promise<SupporterGrant[]> {
	const rows = await db
		.selectFrom('supporter_grants')
		.select([
			'id',
			'amount_cents',
			'days',
			'granted_at',
			'expires_at',
			'plan_type',
			'provider',
			'provider_txn_id'
		])
		.where('user_id', '=', userId)
		.orderBy('granted_at', 'desc')
		.execute();

	return rows.map((r) => ({
		id: String(r.id),
		amountCents: r.amount_cents,
		days: r.days,
		grantedAt: toIso(r.granted_at),
		expiresAt: toIso(r.expires_at),
		planType: r.plan_type,
		provider: r.provider,
		providerTxnId: r.provider_txn_id
	}));
}

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
			grantCount: 0,
			since: null,
			latestPlan: null,
			badges: []
		};
	}

	const now = Date.now();
	const expiresAt = toIso(rows[0].expires_at);
	const maxExpires = new Date(expiresAt).getTime();
	const active = maxExpires > now;
	// "Window Maxxing": their furthest expiry reaches the cap, so there's no room
	// to buy even one more day. Gated on `active` so it can't spuriously fire for
	// everyone once the cap date itself passes.
	const windowMaxed = active && daysAllowedBeforeCap(expiresAt, now) === 0;
	const totalCents = rows.reduce((sum, r) => sum + r.amount_cents, 0);
	const since = rows.reduce<string>((min, r) => {
		const g = toIso(r.granted_at);
		return min === '' || g < min ? g : min;
	}, '');

	return {
		active,
		expiresAt,
		daysLeft: active ? Math.ceil((maxExpires - now) / DAY_MS) : 0,
		totalCents,
		grantCount: rows.length,
		since: since || null,
		latestPlan: rows[0].plan_type,
		// Badges are earned by the dollar amount of each pledge (== days for the
		// $1/day plan; $20 for the one-time, which earns nothing), plus the
		// window-context "Window Maxxing" badge when they've reached the cap.
		badges: [
			...earnedBadges(rows.map((r) => r.amount_cents / 100)),
			...(windowMaxed ? [MAXXING_BADGE] : [])
		]
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
 *
 * Returns true when a new grant was actually recorded, false when this
 * transaction had already been recorded — so callers can act (e.g. notify)
 * only on the first, real delivery and stay quiet on webhook redeliveries.
 */
export async function grantSupporter(input: GrantInput): Promise<boolean> {
	// Idempotency: bail if we've already recorded this transaction.
	const existing = await db
		.selectFrom('supporter_grants')
		.select('id')
		.where('provider_txn_id', '=', input.providerTxnId)
		.executeTakeFirst();
	if (existing) return false;

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

	const result = await db
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

	// 0 inserted rows means a concurrent delivery won the conflict — not a new grant.
	return (result[0]?.numInsertedOrUpdatedRows ?? 0n) > 0n;
}
