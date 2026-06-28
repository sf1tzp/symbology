import { layout, button, footerText, type RenderedEmail } from './layout';

export interface VerifyEmailProps {
	/** Better Auth's tokenized verification link. */
	url: string;
	/** The user's display name, if we have one. */
	name?: string | null;
}

/**
 * Account verification. Deliverability-critical, so keep it plain: one clear CTA,
 * the raw URL as a fallback, and the "didn't sign up?" reassurance line.
 */
export function verifyEmail({ url, name }: VerifyEmailProps): RenderedEmail {
	const hi = name ? `Hi ${name},` : 'Welcome,';

	const html = layout({
		preview: 'Confirm your email to finish setting up your Symbology account.',
		bodyHtml: `
			<p style="margin: 0 0 16px;">${hi}</p>
			<p style="margin: 0 0 8px;">Confirm your email address to finish setting up your Symbology account.</p>
			${button(url, 'Verify email')}
			<p style="margin: 0 0 8px; font-size: 13px; color: #6b7280;">Or paste this link into your browser:</p>
			<p style="margin: 0 0 16px; font-size: 13px; word-break: break-all;"><a href="${url}" style="color: #0f766e;">${url}</a></p>
			<p style="margin: 16px 0 0; font-size: 13px; color: #6b7280;">This link expires in 24 hours. Didn't sign up? You can safely ignore this email.</p>
		`
	});

	const text = `${hi}

Confirm your email address to finish setting up your Symbology account:

${url}

This link expires in 24 hours. Didn't sign up? You can safely ignore this email.

—
${footerText()}`;

	return { subject: 'Verify your email · Symbology', html, text };
}
