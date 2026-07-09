import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getSupporterGrants } from '$lib/server/db/supporter';
import { getReceiptUrl } from '$lib/server/stripe';

/**
 * Billing history — the full supporter-grant ledger for the signed-in user, each
 * row enriched with its Stripe receipt URL. Receipt lookups are best-effort and
 * run in parallel; a grant whose receipt can't be resolved just renders without
 * a link.
 */
export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		redirect(302, `/login?returnTo=${encodeURIComponent(url.pathname)}`);
	}

	const grants = await getSupporterGrants(locals.user.id);
	const receipts = await Promise.all(
		grants.map((g) => (g.provider === 'stripe' ? getReceiptUrl(g.providerTxnId) : null))
	);

	return {
		grants: grants.map((g, i) => ({ ...g, receiptUrl: receipts[i] }))
	};
};
