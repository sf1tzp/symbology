/**
 * Anonymous view meter — a soft sign-up wall for signed-out visitors.
 *
 * All 10-K and 10-Q synthesis is free to *any signed-in account*; support is a
 * donation, not a paywall. To turn readers into accounts we meter guests by
 * *distinct company*: a visitor can read everything under `FREE_COMPANY_LIMIT`
 * companies, and the next new company shows a "create a free account" wall.
 *
 * State lives in a single httpOnly cookie holding the company ids a guest has
 * opened (capped at the limit). Clearing cookies resets the meter — acceptable
 * for a nudge, not a hard entitlement. Signed-in users are never metered.
 */
import type { Cookies } from '@sveltejs/kit';
import { anonMeterEnabled } from '$lib/features';
import { FREE_COMPANY_LIMIT } from '$lib/utils/lock';

const COOKIE = 'sym_meter';
const MAX_AGE = 60 * 60 * 24 * 180; // ~180 days

export interface MeterResult {
	/** True = this company is beyond the guest's budget; show the sign-up wall. */
	metered: boolean;
	/** Distinct companies the guest has opened so far. */
	count: number;
	/** The free budget (`FREE_COMPANY_LIMIT`). */
	limit: number;
}

/**
 * Decide whether a viewer may read a company's synthesis, recording the view
 * against the guest budget as a side effect.
 *
 * `hasContent` gates the accounting: a page with no synthesis to withhold never
 * charges the meter (nothing to gate), so guests aren't billed for empty pages.
 * Already-seen companies are always free and don't advance the count.
 */
export function checkCompanyView(opts: {
	cookies: Cookies;
	user: { id: string } | null | undefined;
	companyId: string;
	hasContent: boolean;
}): MeterResult {
	const { cookies, user, companyId, hasContent } = opts;
	const limit = FREE_COMPANY_LIMIT;

	// Signed-in accounts and a disabled meter never hit the wall.
	if (user || !anonMeterEnabled) return { metered: false, count: 0, limit };

	const seen = parse(cookies.get(COOKIE));

	// Nothing to gate, or a company they've already opened: free, no change.
	if (!hasContent || seen.includes(companyId)) {
		return { metered: false, count: seen.length, limit };
	}

	// Budget left: record this new company and let them read it.
	if (seen.length < limit) {
		write(cookies, [...seen, companyId]);
		return { metered: false, count: seen.length + 1, limit };
	}

	// Out of budget on a new company — this is the one we wall (not recorded, so
	// the guest can still get in by signing up rather than being stuck at N+1).
	return { metered: true, count: seen.length, limit };
}

function parse(raw: string | undefined): string[] {
	if (!raw) return [];
	try {
		const value = JSON.parse(raw);
		if (!Array.isArray(value)) return [];
		return value.filter((x): x is string => typeof x === 'string').slice(0, FREE_COMPANY_LIMIT);
	} catch {
		return [];
	}
}

function write(cookies: Cookies, ids: string[]): void {
	cookies.set(COOKIE, JSON.stringify(ids.slice(0, FREE_COMPANY_LIMIT)), {
		path: '/',
		httpOnly: true,
		sameSite: 'lax',
		maxAge: MAX_AGE
	});
}
