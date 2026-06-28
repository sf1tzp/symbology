/**
 * Shared HTML shell for transactional email. Email clients are stuck in ~2005:
 * use a centered table, inline styles, and web-safe fallbacks rather than modern
 * CSS. Each template fills `bodyHtml`; this wraps it with the Symbology wordmark
 * and a footer. Keep it plain — these are receipts and security mail, not
 * marketing.
 */

import { env } from '$env/dynamic/private';

const BRAND = '#0f766e'; // teal — matches the app's `text-teal-2` accent
const INK = '#1a1a1a';
const MUTED = '#6b7280';
const BG = '#f4f4f5';

/** What every template returns — fed straight into `sendEmail`. */
export interface RenderedEmail {
	subject: string;
	html: string;
	text: string;
}

/**
 * Absolute links to the legal pages. Email clients can't resolve relative URLs,
 * so these are built off `BETTER_AUTH_URL` (the same base every email link uses).
 * Falls back to bare paths if the base is unset, so dev rendering never throws.
 */
function legalUrls(): { terms: string; privacy: string } {
	const base = env.BETTER_AUTH_URL;
	if (!base) return { terms: '/terms', privacy: '/privacy' };
	return {
		terms: new URL('/terms', base).toString(),
		privacy: new URL('/privacy', base).toString()
	};
}

/**
 * Plain-text footer mirroring the HTML one. Templates build their own text body
 * (there's no text layout), so they append this to keep the Terms/Privacy links
 * in every email.
 */
export function footerText(): string {
	const { terms, privacy } = legalUrls();
	return `Symbology · SEC filing intelligence
Questions? Reply to this email.
Terms: ${terms}
Privacy: ${privacy}`;
}

/** A single, obvious call-to-action button. */
export function button(href: string, label: string): string {
	return `<table role="presentation" cellpadding="0" cellspacing="0" style="margin: 28px 0;">
		<tr><td style="border-radius: 8px; background: ${BRAND};">
			<a href="${href}" target="_blank"
				style="display: inline-block; padding: 12px 28px; font-size: 15px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 8px;">${label}</a>
		</td></tr>
	</table>`;
}

export interface LayoutInput {
	/** Preheader — the grey preview snippet inboxes show next to the subject. */
	preview: string;
	bodyHtml: string;
}

export function layout({ preview, bodyHtml }: LayoutInput): string {
	return `<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<meta name="color-scheme" content="light" />
</head>
<body style="margin: 0; padding: 0; background: ${BG};">
	<span style="display: none; max-height: 0; overflow: hidden; opacity: 0;">${preview}</span>
	<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: ${BG}; padding: 32px 16px;">
		<tr><td align="center">
			<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
				style="max-width: 480px; background: #ffffff; border-radius: 12px; border: 1px solid #e4e4e7;">
				<tr><td style="padding: 32px 32px 8px 32px;">
					<div style="font-size: 18px; font-weight: 700; letter-spacing: -0.01em; color: ${BRAND};">Symbology</div>
				</td></tr>
				<tr><td style="padding: 8px 32px 32px 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 15px; line-height: 1.6; color: ${INK};">
					${bodyHtml}
				</td></tr>
			</table>
			<div style="max-width: 480px; padding: 20px 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 12px; line-height: 1.5; color: ${MUTED};">
				Symbology · SEC filing intelligence<br />
				Questions? Reply to this email.<br />
				<a href="${legalUrls().terms}" target="_blank" style="color: ${MUTED}; text-decoration: underline;">Terms of Service</a>
				&nbsp;·&nbsp;
				<a href="${legalUrls().privacy}" target="_blank" style="color: ${MUTED}; text-decoration: underline;">Privacy Policy</a>
			</div>
		</td></tr>
	</table>
</body>
</html>`;
}
