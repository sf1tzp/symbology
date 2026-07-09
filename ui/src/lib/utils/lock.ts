/**
 * Client-safe locked-content vocabulary, shared by the server gating policy
 * (`$lib/server/gating`), the anonymous view meter (`$lib/server/meter`), and
 * the pages that render LockedBlock. Kept free of any server-only imports so it
 * can be used in `+page.svelte` components.
 */

/** Years of 10-K synthesis a free (non-supporter) account can read. */
export const FREE_HISTORY_YEARS = 5;

/** Distinct companies a signed-out visitor may read before the sign-up wall. */
export const FREE_COMPANY_LIMIT = 5;

/**
 * Non-null = the synthesis is withheld from this viewer, and why:
 *   - `history` — a supporter perk: 10-K synthesis older than the free window.
 *   - `meter`   — a sign-up nudge: a guest has spent their free-company budget.
 */
export type LockReason = 'history' | 'meter';

/** Editorial copy + CTA for a lock reason — everything a LockedBlock renders. */
export interface LockCopy {
	title: string;
	note: string;
	badge: string;
	cta: string;
	href: string;
}

export function lockCopy(reason: LockReason): LockCopy {
	if (reason === 'meter') {
		return {
			title: "You've reached the free preview",
			note: `You've read synthesis for ${FREE_COMPANY_LIMIT} companies as a guest. Create a free account to keep reading — unlimited 10-K and 10-Q synthesis, no payment, just an email.`,
			badge: 'Free account',
			cta: 'Create a free account',
			href: '/signup'
		};
	}
	return {
		title: 'This synthesis is beyond the free window',
		note: `Free accounts get the last ${FREE_HISTORY_YEARS} years of 10-K synthesis. Supporters read the full history. The raw filing remains free to view.`,
		badge: 'Supporter',
		cta: 'Become a supporter',
		href: '/support'
	};
}
