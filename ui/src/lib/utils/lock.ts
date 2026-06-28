/**
 * Client-safe locked-content vocabulary, shared by the server gating policy
 * (`$lib/server/gating`) and the pages that render LockedBlock. Kept free of any
 * server-only imports so it can be used in `+page.svelte` components.
 */
export const FREE_HISTORY_YEARS = 5;

/** Non-null = the synthesis is locked for this viewer, and why. */
export type LockReason = 'quarterly' | 'history';

/** Editorial copy for a lock reason — the LockedBlock title + note. */
export function lockCopy(reason: LockReason): { title: string; note: string } {
	if (reason === 'quarterly') {
		return {
			title: 'Quarterly synthesis is a supporter perk',
			note: 'The distilled 10-Q report — quarter-over-quarter, with citations — is unlocked for supporters. The raw filing stays free on this page, and 10-K annual synthesis is free for everyone.'
		};
	}
	return {
		title: 'This synthesis is beyond the free window',
		note: `Free accounts get the last ${FREE_HISTORY_YEARS} years of 10-K synthesis. Supporters read the full history. The raw filing remains free to view.`
	};
}
