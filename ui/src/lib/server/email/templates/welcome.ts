import { layout, button, footerText, type RenderedEmail } from './layout';

export interface WelcomeProps {
	name?: string | null;
	/** Link into the app — the watchlist hub. */
	appUrl: string;
}

/**
 * Sent once, right after a user verifies their email. Sets expectations and
 * points them at the first useful thing (their watchlist).
 */
export function welcome({ name, appUrl }: WelcomeProps): RenderedEmail {
	const hi = name ? `Welcome, ${name}!` : 'Welcome!';

	const html = layout({
		preview: 'Your Symbology account is ready — start building your watchlist.',
		bodyHtml: `
			<p style="margin: 0 0 16px;">${hi}</p>
			<p style="margin: 0 0 8px;">Your email is verified and your Symbology account is ready to go.</p>
			<p style="margin: 0 0 8px;">Symbology turns SEC filings into plain-language intelligence. Add companies to your watchlist to keep an eye on what they file.</p>
			${button(appUrl, 'Go to your watchlist')}
			<p style="margin: 16px 0 0; font-size: 13px; color: #6b7280;">Glad to have you on board.</p>
		`
	});

	const text = `${hi}

Your email is verified and your Symbology account is ready to go.

Symbology turns SEC filings into plain-language intelligence. Add companies to your watchlist to keep an eye on what they file:

${appUrl}

Glad to have you on board.

—
${footerText()}`;

	return { subject: 'Welcome to Symbology', html, text };
}
