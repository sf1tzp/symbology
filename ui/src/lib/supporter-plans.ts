/**
 * Supporter plan constants, amount "easter-egg" badges, and the duration-cap
 * policy. Pure module (no DB / no secrets) so it can be shared by the support
 * page UI and the server-side checkout validation.
 */

export const DAY_MS = 86_400_000;

/** Pick-your-duration plan ($1/day): price === days. */
export const MIN_DAYS = 33;
export const DEFAULT_DAYS = 33;

/**
 * A pledge of exactly 888 days earns the lucky "利是" badge (888 ≈ prosperity).
 * No longer the slider's ceiling — the duration plan now runs the full range up
 * to the policy cap below — just a fun easter-egg threshold.
 */
export const LUCKY_888 = 888;

/** Flat one-time plan: $20 → 14 days. */
export const ONE_TIME_DAYS = 14;
export const ONE_TIME_PRICE = 20;

/**
 * Hard policy cap: no supporter window may extend past this instant. The
 * duration slider runs the full range up to this cap, and top-ups likewise
 * can't be stacked past it. We may introduce new tiers/pricing as the project
 * matures, so we don't commit supporter status at this price beyond then.
 */
export const SUPPORT_CAP_ISO = '2028-12-31T23:59:59.999Z';

export type BadgeColor = 'green' | 'orange' | 'blue' | 'purple' | 'red' | 'gold' | 'gray';

/** Stable identity for a badge type (one badge can be earned by several amounts). */
export type BadgeKey =
	| 'magic'
	| 'fives'
	| 'sevens'
	| 'max'
	| 'maxxing'
	| 'answer'
	| 'class'
	| 'catch'
	| 'sparta'
	| 'daLou'
	| 'spark'
	| 'notfound'
	| 'herbMon'
	| 'slayer'
	| 'jackpot'
	| 'eightOhEight'
	| 'fib'
	| 'spin'
	| 'mph'
	| 'boiling'
	| 'overflow'
	| 'books'
	| 'pow2'
	| 'prime';

export interface AmountBadge {
	key: BadgeKey;
	emoji: string;
	label: string;
	color: BadgeColor;
}

/**
 * Exact-amount easter-egg badges, highest precedence first: when a pledge
 * matches more than one row the earlier one wins (e.g. 256 takes "Integer
 * Overflow", not the generic Power-of-2 badge). A single badge identity can be
 * earned by several amounts (e.g. 33 and 333). Emoji are placeholders pending
 * final icon art.
 */
const EXACT_BADGES: ReadonlyArray<{ amounts: readonly number[]; badge: AmountBadge }> = [
	{ amounts: [888], badge: { key: 'max', emoji: '🧧', label: '利是', color: 'red' } },
	{
		amounts: [33, 333],
		badge: { key: 'magic', emoji: '✨', label: "Three That's The Magic Number", color: 'green' }
	},
	{
		amounts: [55, 555],
		badge: { key: 'fives', emoji: '♣️', label: "I got 5's on it", color: 'orange' }
	},
	{
		amounts: [77, 777],
		badge: { key: 'sevens', emoji: '7️⃣', label: 'Lucky Number 7', color: 'blue' }
	},
	// ── Pop culture & gaming ──
	{
		amounts: [42],
		badge: { key: 'answer', emoji: '🌌', label: 'I finally got the answer!', color: 'purple' }
	},
	{ amounts: [101], badge: { key: 'class', emoji: '🎓', label: 'Back to Class', color: 'blue' } },
	{
		amounts: [151],
		badge: { key: 'catch', emoji: '🔴', label: "Gotta Catch 'em All", color: 'gold' }
	},
	{
		amounts: [300],
		badge: { key: 'sparta', emoji: '🛡️', label: 'This.. Is.. SYMBOLOGY!!!', color: 'red' }
	},
	{
		amounts: [314],
		badge: { key: 'daLou', emoji: '🎉', label: 'St. Louis Mentioned', color: 'blue' }
	},
	{ amounts: [343], badge: { key: 'spark', emoji: '💡', label: 'Guilty Spark', color: 'green' } },
	{
		amounts: [404],
		badge: { key: 'notfound', emoji: '🚫', label: 'Support Not Found', color: 'gray' }
	},
	{
		amounts: [420],
		badge: { key: 'herbMon', emoji: '', label: 'Head in the Clouds', color: 'green' }
	},
	{
		amounts: [666],
		badge: { key: 'slayer', emoji: '🤘', label: 'Play Some Slayer', color: 'red' }
	},
	{ amounts: [777], badge: { key: 'jackpot', emoji: '🎰', label: 'JackPot!', color: 'gold' } },
	{
		amounts: [808],
		badge: { key: 'eightOhEight', emoji: '🔊', label: '4x15s in the Trunk', color: 'gold' }
	},
	// ── Mathematical achievements ──
	{
		amounts: [144],
		badge: { key: 'fib', emoji: '🌀', label: '12 × 12 == fib(12)', color: 'purple' }
	},
	{
		amounts: [360],
		badge: { key: 'spin', emoji: '🔄', label: "I'll try spinning", color: 'blue' }
	},
	// ── Science & tech ──
	{
		amounts: [88],
		badge: { key: 'mph', emoji: '🚗', label: 'EIGHTY-EIGHT MILES PER HOUR!', color: 'orange' }
	},
	{
		amounts: [212],
		badge: { key: 'boiling', emoji: '🌡️', label: 'Reached the Boiling Point', color: 'orange' }
	},
	{
		amounts: [256],
		badge: { key: 'overflow', emoji: '💥', label: 'Integer Overflow', color: 'orange' }
	},
	{
		amounts: [451],
		badge: { key: 'books', emoji: '🔥', label: 'Read more Books', color: 'orange' }
	}
];

/**
 * Awarded when a pledge takes the supporter window all the way to the policy
 * cap (Dec 31 2028). Not amount-derived like the rest — it depends on the
 * window, not the number — so the support page and server append it explicitly.
 */
export const MAXXING_BADGE: AmountBadge = {
	key: 'maxxing',
	emoji: '👑',
	label: 'Window Maxxing',
	color: 'gold'
};

/** Every known badge key, kept in sync with the table + the generic/context badges. */
const BADGE_KEYS: BadgeKey[] = [
	...EXACT_BADGES.map((r) => r.badge.key),
	MAXXING_BADGE.key,
	'pow2',
	'prime'
];

/** Readable text/tint colour per badge colour — shared by every badge surface. */
export const BADGE_HEX: Record<BadgeColor, string> = {
	green: 'var(--teal-2)',
	orange: '#c2761b',
	blue: '#2f6fb3',
	purple: '#7a52c9',
	red: '#c0392b',
	gold: '#b8860b',
	gray: '#52525b'
};

function isPrime(n: number): boolean {
	if (!Number.isInteger(n) || n < 2) return false;
	if (n % 2 === 0) return n === 2;
	for (let i = 3; i * i <= n; i += 2) {
		if (n % i === 0) return false;
	}
	return true;
}

/** True for 4, 8, 16, 32, … (excludes 1 and 2 — too small to be reachable anyway). */
function isPowerOfTwo(n: number): boolean {
	return Number.isInteger(n) && n > 2 && (n & (n - 1)) === 0;
}

/**
 * Every fun badge a given pledge amount earns — they stack, so an amount can
 * claim several (e.g. 256 is both "Integer Overflow" and "Power of 2"; 777 is
 * both "JackPot!" and "Lucky Number 7"). Returned in display order: themed
 * exact-amount badges first (table order), then the generic Power-of-2 and
 * PRIME badges. Empty for an ordinary amount.
 */
export function amountBadges(n: number): AmountBadge[] {
	const out: AmountBadge[] = [];
	for (const row of EXACT_BADGES) {
		if (row.amounts.includes(n)) out.push(row.badge);
	}
	if (isPowerOfTwo(n))
		out.push({ key: 'pow2', emoji: '🧮', label: `Power of 2 (2^${Math.log2(n)})`, color: 'gold' });
	if (isPrime(n)) out.push({ key: 'prime', emoji: 'ℙ', label: 'PRIME', color: 'purple' });
	return out;
}

/**
 * The "milestone" pledge amounts within [min, max] worth snapping the slider to:
 * every themed exact-amount badge plus each power of 2. Bare primes are left out
 * — they're far too dense to be useful magnets. Sorted ascending, de-duplicated.
 */
export function badgeMilestones(min: number, max: number): number[] {
	const set = new Set<number>();
	for (const row of EXACT_BADGES) {
		for (const a of row.amounts) if (a >= min && a <= max) set.add(a);
	}
	for (let p = 4; p <= max; p *= 2) if (p >= min) set.add(p);
	return [...set].sort((a, b) => a - b);
}

/**
 * Distinct badges earned across a set of pledge amounts (dollars), in first-seen
 * order. One badge type counts once even if earned by several pledges.
 */
export function earnedBadges(amounts: number[]): AmountBadge[] {
	const seen = new Set<BadgeKey>();
	const out: AmountBadge[] = [];
	for (const amount of amounts) {
		for (const b of amountBadges(amount)) {
			if (!seen.has(b.key)) {
				seen.add(b.key);
				out.push(b);
			}
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
