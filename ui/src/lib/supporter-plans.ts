/**
 * Supporter plan constants, amount "easter-egg" badges, and the duration-cap
 * policy. Pure module (no DB / no secrets) so it can be shared by the support
 * page UI and the server-side checkout validation.
 */

export const DAY_MS = 86_400_000;

/** Pick-your-duration plan ($1/day): price === days. */
export const MIN_DAYS = 33;
export const MAX_DAYS = 888;
export const DEFAULT_DAYS = 33;

/** Flat one-time plan: $20 → 14 days. */
export const ONE_TIME_DAYS = 14;
export const ONE_TIME_PRICE = 20;

/**
 * Hard policy cap: no supporter window may extend past this instant. A single
 * 888-day pledge from launch lands in late Nov 2028 — comfortably inside the
 * cap — but top-ups can't be stacked past the end of 2028. We may introduce new
 * tiers/pricing as the project matures, so we don't commit supporter status at
 * this price beyond then.
 */
export const SUPPORT_CAP_ISO = '2028-12-31T23:59:59.999Z';

export type BadgeColor = 'green' | 'orange' | 'blue' | 'purple' | 'red';

/** Stable identity for a badge type (one badge can be earned by several amounts). */
export type BadgeKey = 'magic' | 'fives' | 'sevens' | 'prime' | 'max';

export interface AmountBadge {
	key: BadgeKey;
	emoji: string;
	label: string;
	color: BadgeColor;
}

const BADGE_KEYS: BadgeKey[] = ['magic', 'fives', 'sevens', 'prime', 'max'];

/** Readable text/tint colour per badge colour — shared by every badge surface. */
export const BADGE_HEX: Record<BadgeColor, string> = {
	green: 'var(--teal-2)',
	orange: '#c2761b',
	blue: '#2f6fb3',
	purple: '#7a52c9',
	red: '#c0392b'
};

function isPrime(n: number): boolean {
	if (!Number.isInteger(n) || n < 2) return false;
	if (n % 2 === 0) return n === 2;
	for (let i = 3; i * i <= n; i += 2) {
		if (n % i === 0) return false;
	}
	return true;
}

/**
 * The fun badge a given pledge amount earns, or null for an ordinary amount.
 * The explicit lucky numbers take precedence over the catch-all PRIME badge
 * (none of them overlap in practice, since they're all composite).
 */
export function amountBadge(n: number): AmountBadge | null {
	if (n === MAX_DAYS) return { key: 'max', emoji: '🧧', label: '利是', color: 'red' };
	if (n === 33 || n === 333)
		return { key: 'magic', emoji: '✨', label: 'The magic number', color: 'green' };
	if (n === 55 || n === 555)
		return { key: 'fives', emoji: '♣️', label: "I got 5's on it", color: 'orange' };
	if (n === 77 || n === 777)
		return { key: 'sevens', emoji: '🎰', label: 'Lucky Number 7', color: 'blue' };
	if (isPrime(n)) return { key: 'prime', emoji: 'ℙ', label: 'PRIME', color: 'purple' };
	return null;
}

/**
 * Distinct badges earned across a set of pledge amounts (dollars), in first-seen
 * order. One badge type counts once even if earned by several pledges.
 */
export function earnedBadges(amounts: number[]): AmountBadge[] {
	const seen = new Set<BadgeKey>();
	const out: AmountBadge[] = [];
	for (const amount of amounts) {
		const b = amountBadge(amount);
		if (b && !seen.has(b.key)) {
			seen.add(b.key);
			out.push(b);
		}
	}
	return out;
}

// ── Avatar badge: a supporter may use an earned badge's icon in place of their
// initials. The chosen BadgeKey persists raw in Better Auth's `user.avatarBadge`
// custom field (account-domain data, carried in the session). Display is still
// gated on the badge being actually earned, so an unknown/unearned value here
// just falls back to initials.

/** Narrow a stored avatar-badge value to a known BadgeKey, or null. */
export function coerceBadgeKey(value: string | null | undefined): BadgeKey | null {
	return value && BADGE_KEYS.includes(value as BadgeKey) ? (value as BadgeKey) : null;
}

/**
 * How many more supporter-days a user may still buy before hitting the cap,
 * given their current furthest expiry (ISO, or null if they have none) and the
 * current time. New windows stack onto the later of "now" and the current
 * expiry, so the allowance shrinks as that base approaches the cap.
 */
export function daysAllowedBeforeCap(currentExpiryIso: string | null, now: number): number {
	const expiry = currentExpiryIso ? Date.parse(currentExpiryIso) : now;
	const base = Math.max(now, expiry);
	return Math.max(0, Math.floor((Date.parse(SUPPORT_CAP_ISO) - base) / DAY_MS));
}
