/**
 * Content gating policy — one place that decides what a viewer may see, so the
 * company page, filing page, and any future surface stay consistent.
 *
 * Raw EDGAR filings are ALWAYS free, and all recent 10-K and 10-Q synthesis is
 * free to any signed-in account — support is a donation, not a paywall. Two
 * gates remain:
 *   - History (this module): 10-K synthesis older than `FREE_HISTORY_YEARS` is
 *     a supporter perk. 10-Q and recent 10-K synthesis are free.
 *   - The anonymous view meter (`$lib/server/meter`): signed-out guests get a
 *     budget of companies before a sign-up wall.
 *
 * Enforcement is server-side: a locked surface withholds the generated text
 * from the payload and returns a `LockReason` the page renders as an editorial
 * LockedBlock. The raw documents are served regardless.
 */
import { isSupporter } from '$lib/server/db/supporter';
import { supportEnabled } from '$lib/features';
import { FREE_HISTORY_YEARS, type LockReason } from '$lib/utils/lock';

export { FREE_HISTORY_YEARS, lockCopy, type LockReason } from '$lib/utils/lock';

/** A form is quarterly if it's a 10-Q (incl. amendments like 10-Q/A). */
export function isQuarterly(form: string | null | undefined): boolean {
	return !!form && form.toUpperCase().startsWith('10-Q');
}

/** True if a date sits before the free 10-K analysis window. */
export function olderThanFreeWindow(dateIso: string | null | undefined): boolean {
	if (!dateIso) return false;
	const cutoff = new Date();
	cutoff.setFullYear(cutoff.getFullYear() - FREE_HISTORY_YEARS);
	return new Date(dateIso).getTime() < cutoff.getTime();
}

/**
 * Why a viewer can't see a specific *filing's* generated analysis, or null if
 * they can. Only the >5y 10-K history perk is gated here; supporters (and any
 * form within the free window) short-circuit to null. Company-page narratives
 * are always built from recent filings, so they have no history gate — the only
 * gate there is the anonymous meter, handled in the route.
 */
export function filingAnalysisLock(
	form: string | null | undefined,
	filingDate: string | null | undefined,
	supporter: boolean
): LockReason | null {
	if (supporter) return null;
	if (isQuarterly(form)) return null;
	if (olderThanFreeWindow(filingDate)) return 'history';
	return null;
}

/**
 * Resolve whether a viewer gets supporter-level access. While the supporter
 * program is gated off pre-launch (`PUBLIC_SUPPORT_ENABLED` not "true"), the tier
 * effectively doesn't exist yet, so everyone is treated as a supporter and
 * nothing is gated. Once it's live this falls back to the real per-user check
 * (false when signed out).
 */
export async function viewerIsSupporter(user: { id: string } | null | undefined): Promise<boolean> {
	if (!supportEnabled) return true;
	return user ? isSupporter(user.id) : false;
}
