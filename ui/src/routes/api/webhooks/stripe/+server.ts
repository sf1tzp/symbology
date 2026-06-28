import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import Stripe from 'stripe';
import { getStripe } from '$lib/server/stripe';
import { grantSupporter } from '$lib/server/db/supporter';

/**
 * Stripe webhook. The ONLY place supporter days are granted — never trust the
 * client. We verify the signature, then on `checkout.session.completed` read
 * the user/plan from the session metadata and record the grant idempotently
 * (Stripe may deliver the same event more than once).
 */
export const POST: RequestHandler = async ({ request }) => {
	const secret = env.STRIPE_WEBHOOK_SECRET;
	if (!secret) {
		console.error('STRIPE_WEBHOOK_SECRET is not configured');
		throw error(500, 'Webhook not configured');
	}

	const signature = request.headers.get('stripe-signature');
	if (!signature) throw error(400, 'Missing stripe-signature header');

	// constructEvent needs the raw body exactly as sent.
	const payload = await request.text();

	let event: Stripe.Event;
	try {
		event = getStripe().webhooks.constructEvent(payload, signature, secret);
	} catch (err) {
		console.error('Stripe signature verification failed', err);
		throw error(400, 'Invalid signature');
	}

	if (event.type === 'checkout.session.completed') {
		const session = event.data.object as Stripe.Checkout.Session;

		// Only grant once payment is actually settled.
		if (session.payment_status !== 'paid') {
			return json({ received: true });
		}

		const userId = session.metadata?.user_id ?? session.client_reference_id ?? null;
		const days = Number(session.metadata?.days ?? 0);
		const planType = session.metadata?.plan_type ?? 'duration';
		// Prefer the PaymentIntent id as the idempotency key; fall back to the
		// session id if it's somehow absent.
		const txnId =
			(typeof session.payment_intent === 'string'
				? session.payment_intent
				: session.payment_intent?.id) ?? session.id;

		if (!userId || !Number.isFinite(days) || days <= 0) {
			console.error('checkout.session.completed missing grant metadata', {
				id: session.id,
				userId,
				days
			});
			// 200 so Stripe doesn't retry a permanently-malformed event.
			return json({ received: true });
		}

		try {
			await grantSupporter({
				userId,
				days,
				amountCents: session.amount_total ?? days * 100,
				planType,
				provider: 'stripe',
				providerTxnId: txnId
			});
		} catch (err) {
			console.error('failed to record supporter grant', err);
			// 500 → Stripe retries; grantSupporter is idempotent so retries are safe.
			throw error(500, 'Failed to record grant');
		}
	}

	return json({ received: true });
};
