import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createCheckoutSession, resolvePlan } from '$lib/server/stripe';
import { getSupporterStatus } from '$lib/server/db/supporter';
import { daysAllowedBeforeCap } from '$lib/supporter-plans';
import { supportEnabled } from '$lib/features';

export const load: PageServerLoad = async ({ locals }) => {
	// Payments aren't live yet — keep the whole support surface dark behind the
	// runtime flag, bouncing visitors home rather than showing a buyable page.
	if (!supportEnabled) {
		redirect(307, '/');
	}

	// Let the page tailor its CTAs (e.g. "already a supporter") without a second
	// round-trip. Anonymous visitors just get null.
	return {
		supporter: locals.user ? await getSupporterStatus(locals.user.id) : null
	};
};

export const actions: Actions = {
	/**
	 * Start a Stripe Checkout session for the chosen plan and redirect the user
	 * to Stripe's hosted page. Requires sign-in (we need an account to grant the
	 * days to); anonymous users are bounced to login with a returnTo back here.
	 */
	checkout: async ({ request, locals, url }) => {
		// Defence in depth: the page redirects when support is off, but never let a
		// stray POST reach Stripe while the surface is gated.
		if (!supportEnabled) {
			redirect(307, '/');
		}

		if (!locals.user) {
			redirect(303, `/login?returnTo=${encodeURIComponent('/support')}`);
		}

		const data = await request.formData();
		const plan = String(data.get('plan') ?? '');
		const days = Number(data.get('days') ?? 0);

		let checkoutUrl: string;
		try {
			const resolved = resolvePlan(plan, days);

			// Enforce the supporter-window cap (Dec 31 2028): a pledge can't stack
			// past it. We re-check server-side so a stale or tampered client can't
			// buy beyond what the policy allows.
			const status = await getSupporterStatus(locals.user.id);
			const allowed = daysAllowedBeforeCap(status.expiresAt, Date.now());
			if (resolved.days > allowed) {
				return fail(400, {
					message:
						allowed > 0
							? `That would extend your supporter window past our current cap (Dec 31, 2028). You can add up to ${allowed} more ${allowed === 1 ? 'day' : 'days'} right now.`
							: `Your supporter window already reaches our current cap (Dec 31, 2028) — there's nothing more to add right now.`
				});
			}

			checkoutUrl = await createCheckoutSession({
				userId: locals.user.id,
				email: locals.user.email,
				plan: resolved,
				origin: url.origin
			});
		} catch (err) {
			console.error('checkout failed', err);
			return fail(400, { message: 'Could not start checkout. Please try again.' });
		}

		redirect(303, checkoutUrl);
	}
};
