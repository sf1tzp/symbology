import Stripe from 'stripe';
import { env } from '$env/dynamic/private';
import { MIN_DAYS, MAX_DAYS, ONE_TIME_DAYS } from '$lib/supporter-plans';

/**
 * Supporter pricing. Two one-time options (no subscriptions):
 *  - `one`      — flat $20, grants 14 days.
 *  - `duration` — $1/day, slider picks 33–888 days; price === days.
 * Both resolve to a concrete { amountCents, days } here so the checkout action
 * and the webhook agree on what was sold. Day bounds are single-sourced from
 * `$lib/supporter-plans` so the UI and this validation can't drift.
 */
export const DURATION_MIN_DAYS = MIN_DAYS;
export const DURATION_MAX_DAYS = MAX_DAYS;
export const ONE_OFF_DAYS = ONE_TIME_DAYS;
export const ONE_OFF_CENTS = 2000;

export type PlanType = 'one' | 'duration';

export interface ResolvedPlan {
	planType: PlanType;
	days: number;
	amountCents: number;
	/** Human label shown on the Stripe Checkout line item. */
	label: string;
}

/**
 * Resolve a (plan, days) request into a concrete charge. `days` is ignored for
 * the flat `one` plan and clamped to the allowed range for `duration`. Throws
 * on an unknown plan so a malformed request can't create a bogus charge.
 */
export function resolvePlan(plan: string, days: number): ResolvedPlan {
	if (plan === 'one') {
		return {
			planType: 'one',
			days: ONE_OFF_DAYS,
			amountCents: ONE_OFF_CENTS,
			label: `Symbology supporter — ${ONE_OFF_DAYS} days`
		};
	}
	if (plan === 'duration') {
		const d = Math.round(days);
		if (!Number.isFinite(d) || d < DURATION_MIN_DAYS || d > DURATION_MAX_DAYS) {
			throw new Error(`days must be between ${DURATION_MIN_DAYS} and ${DURATION_MAX_DAYS}`);
		}
		return {
			planType: 'duration',
			days: d,
			amountCents: d * 100,
			label: `Symbology supporter — ${d} days`
		};
	}
	throw new Error(`unknown plan: ${plan}`);
}

let _stripe: Stripe | null = null;

/** Lazily-constructed Stripe client. Throws if the secret key is unset. */
export function getStripe(): Stripe {
	if (!_stripe) {
		if (!env.STRIPE_SECRET_KEY) {
			throw new Error('STRIPE_SECRET_KEY is not configured');
		}
		_stripe = new Stripe(env.STRIPE_SECRET_KEY);
	}
	return _stripe;
}

export interface CheckoutParams {
	userId: string;
	email: string;
	plan: ResolvedPlan;
	/** App origin (e.g. https://symbology.online) for success/cancel redirects. */
	origin: string;
}

/**
 * Create a one-time Stripe Checkout Session for a supporter purchase and return
 * its hosted URL. The user id + plan ride in `metadata` (and
 * `client_reference_id`) so the webhook can grant the right days to the right
 * account without trusting the client.
 */
export async function createCheckoutSession(params: CheckoutParams): Promise<string> {
	const { userId, email, plan, origin } = params;
	const session = await getStripe().checkout.sessions.create({
		mode: 'payment',
		customer_email: email,
		client_reference_id: userId,
		line_items: [
			{
				quantity: 1,
				price_data: {
					currency: 'usd',
					unit_amount: plan.amountCents,
					product_data: { name: plan.label }
				}
			}
		],
		metadata: {
			user_id: userId,
			days: String(plan.days),
			plan_type: plan.planType
		},
		// Mirror onto the PaymentIntent too, so the data is present regardless of
		// which object a future webhook handler reads.
		payment_intent_data: {
			metadata: { user_id: userId, days: String(plan.days), plan_type: plan.planType }
		},
		success_url: `${origin}/a/settings?supported=1`,
		cancel_url: `${origin}/support?canceled=1`
	});
	if (!session.url) throw new Error('Stripe did not return a checkout URL');
	return session.url;
}
