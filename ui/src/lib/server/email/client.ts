import { Resend } from 'resend';
import { env } from '$env/dynamic/private';

/**
 * Lazily-constructed Resend client, mirroring the `getStripe()` pattern in
 * `$lib/server/stripe.ts`. Constructed on first use (not at module load) so the
 * app boots even when `RESEND_API_KEY` is unset — the `send.ts` helper checks
 * for the key first and skips sending in that case, so this only runs when a key
 * is actually present.
 */
let client: Resend | null = null;

export function getResend(): Resend {
	if (!client) {
		const key = env.RESEND_API_KEY;
		if (!key) throw new Error('RESEND_API_KEY is not configured');
		client = new Resend(key);
	}
	return client;
}
