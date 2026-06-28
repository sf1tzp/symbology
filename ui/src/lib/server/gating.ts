/**
 * Content gating policy — one place that decides what a free viewer may see, so
 * the company page, filing page, and any future surface stay consistent.
 *
 * Raw EDGAR filings are ALWAYS free; only *generated analysis* is gated. The
 * rules (see MONETIZATION.md):
 *   - 10-Q quarterly analysis is supporter-only.
 *   - 10-K annual analysis is free for the last `FREE_HISTORY_YEARS`; older
 *     analysis is supporter-only.
 *
 * Enforcement is server-side: a locked surface withholds the generated text
 * from the payload entirely and returns a `LockReason` the page renders as an
 * editorial LockedBlock. The raw documents are served regardless.
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
 * they can. `supporter` short-circuits to null (supporters see everything).
 */
export function filingAnalysisLock(
	form: string | null | undefined,
	filingDate: string | null | undefined,
	supporter: boolean
): LockReason | null {
	if (supporter) return null;
	if (isQuarterly(form)) return 'quarterly';
	if (olderThanFreeWindow(filingDate)) return 'history';
	return null;
}

/**
 * Why a viewer can't see a *company page's* narrative for a given form, or null.
 * Company-page narratives are always built from recent filings, so only the
 * quarterly (10-Q) form is gated here — the >5y rule lives on filing pages.
 */
export function companyFormLock(
	form: string | null | undefined,
	supporter: boolean
): LockReason | null {
	if (supporter) return null;
	if (isQuarterly(form)) return 'quarterly';
	return null;
}

/**
 * Resolve whether a viewer gets supporter-level access. While the supporter
 * program is gated off pre-launch (`PUBLIC_SUPPORT_ENABLED` not "true"), the tier
 * effectively doesn't exist yet, so everyone is treated as a supporter and
 * nothing is gated — the analysis, status dashboard, and status feeds are all
 * public. Once it's live this falls back to the real per-user check (false when
 * signed out).
 */
export async function viewerIsSupporter(user: { id: string } | null | undefined): Promise<boolean> {
	if (!supportEnabled) return true;
	return user ? isSupporter(user.id) : false;
}
