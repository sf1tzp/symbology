import { layout, button, type RenderedEmail } from './layout';

export interface ResetPasswordProps {
	/** Better Auth's tokenized reset link. */
	url: string;
	name?: string | null;
}

/**
 * Password reset. Same security pattern as verification: single-use,
 * time-limited token, clear "didn't request this?" escape hatch.
 */
export function resetPassword({ url, name }: ResetPasswordProps): RenderedEmail {
	const hi = name ? `Hi ${name},` : 'Hi,';

	const html = layout({
		preview: 'Reset your Symbology password — this link expires in 1 hour.',
		bodyHtml: `
			<p style="margin: 0 0 16px;">${hi}</p>
			<p style="margin: 0 0 8px;">We received a request to reset your Symbology password. Choose a new one here:</p>
			${button(url, 'Reset password')}
			<p style="margin: 0 0 8px; font-size: 13px; color: #6b7280;">Or paste this link into your browser:</p>
			<p style="margin: 0 0 16px; font-size: 13px; word-break: break-all;"><a href="${url}" style="color: #0f766e;">${url}</a></p>
			<p style="margin: 16px 0 0; font-size: 13px; color: #6b7280;">This link expires in 1 hour and can be used once. If you didn't request a password reset, you can safely ignore this email — your password won't change.</p>
		`
	});

	const text = `${hi}

We received a request to reset your Symbology password. Choose a new one here:

${url}

This link expires in 1 hour and can be used once. If you didn't request a password reset, you can safely ignore this email — your password won't change.`;

	return { subject: 'Reset your password · Symbology', html, text };
}
