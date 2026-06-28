import { env } from '$env/dynamic/private';
import { getResend } from './client';

export interface SendEmailInput {
	/** Recipient address. */
	to: string;
	subject: string;
	/** Rendered HTML body. */
	html: string;
	/** Plain-text alternative — always provide one for deliverability. */
	text: string;
	/**
	 * Optional custom headers. Transactional mail (verify/reset/welcome) sets
	 * none; this exists so the future watch-notification path can attach
	 * List-Unsubscribe without touching this helper.
	 */
	headers?: Record<string, string>;
}

/**
 * The single choke point for outbound email. Centralizes the `from`/`reply-to`
 * identity and degrades gracefully in dev: when `RESEND_API_KEY` is unset the
 * send is skipped with a log line, so local signup/verify/reset flows work
 * without a real key. Returns the Resend message id on success, or null when
 * the send was skipped.
 */
export async function sendEmail(input: SendEmailInput): Promise<string | null> {
	const from = env.RESEND_EMAIL_FROM;

	if (!env.RESEND_API_KEY || !from) {
		console.warn(
			`[email] RESEND_API_KEY/RESEND_EMAIL_FROM not set — skipping "${input.subject}" to ${input.to}`
		);
		return null;
	}

	const replyTo = env.EMAIL_REPLY_TO || undefined;

	const { data, error } = await getResend().emails.send({
		from,
		to: input.to,
		subject: input.subject,
		html: input.html,
		text: input.text,
		...(replyTo ? { replyTo } : {}),
		...(input.headers ? { headers: input.headers } : {})
	});

	if (error) {
		console.error(`[email] failed to send "${input.subject}" to ${input.to}`, error);
		throw new Error(`Resend send failed: ${error.message}`);
	}

	return data?.id ?? null;
}
