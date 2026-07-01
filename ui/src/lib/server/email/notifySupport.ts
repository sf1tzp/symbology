import { env } from '$env/dynamic/private';
import { sendEmail } from './send';

/**
 * Default recipient for internal ops notifications. Overridable via
 * `SUPPORT_NOTIFY_EMAIL` so staging can route elsewhere without a code change.
 */
const DEFAULT_SUPPORT_INBOX = 'support@streetfortress.com';

export interface SupportNotification {
	/** Subject line — prefixed with `[Symbology]` for inbox filtering. */
	subject: string;
	/** Body lines, rendered one per paragraph (html) / line (text). */
	lines: string[];
}

function escapeHtml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

/**
 * Fire-and-forget internal notification to the support inbox. Unlike the
 * user-facing transactional mail, these are plain operational signals (new
 * signup, new supporter payment) with no marketing shell.
 *
 * Deliberately never throws: a notification is observability, and must not
 * break the user-facing flow that triggered it (signup, Stripe webhook). Any
 * failure — Resend outage, missing config — is logged and swallowed. Reuses
 * `sendEmail`, so it inherits the dev-safe skip when Resend isn't configured.
 */
export async function notifySupport(input: SupportNotification): Promise<void> {
	const to = env.SUPPORT_NOTIFY_EMAIL || DEFAULT_SUPPORT_INBOX;
	const subject = `[Symbology] ${input.subject}`;
	const text = input.lines.join('\n');
	const html = input.lines.map((line) => `<p>${escapeHtml(line)}</p>`).join('\n');

	try {
		await sendEmail({ to, subject, html, text });
	} catch (err) {
		console.error(`[email] support notification failed: "${subject}"`, err);
	}
}
