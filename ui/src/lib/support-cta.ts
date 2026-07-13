/**
 * Rotating support-page hero copy. Pure module (no DB / no secrets) so the server
 * `load` can pick a variant and the page can render it. Rotation is chosen
 * server-side (one pick per request) and passed down as an index, so SSR and the
 * first client render agree — picking with Math.random() in the component would
 * hydrate-mismatch.
 */

export interface SupportHeroVariant {
	/** Small mono eyebrow above the headline. */
	eyebrow: string;
	/** Headline, split so the tail can render emphasised (<em>). */
	titleLead: string;
	titleEm: string;
	/** Body paragraphs under the headline. */
	lines: string[];
}

/**
 * The pool of hero pitches, rotated per page load. Each frames the ask a little
 * differently — the fundraiser/backlog angle, the signal-to-noise value angle,
 * and the plain "keep it running" angle — so repeat visitors see variety.
 */
export const SUPPORT_HERO_VARIANTS: readonly SupportHeroVariant[] = [
	{
		eyebrow: 'EARLY-SUPPORTER FUNDRAISER',
		titleLead: 'Help us',
		titleEm: 'catch up.',
		lines: [
			"We're working through a backlog of existing filings — and running a fundraiser to gauge interest in the project.",
			'For just $1/day, secure early access to advanced features and directly fund ongoing synthesis.'
		]
	},
	{
		eyebrow: 'SIGNAL, NOT NOISE',
		titleLead: 'Skip the legalese,',
		titleEm: "read what's changed.",
		lines: [
			'Symbology saves time and effort when researching — skip huge amounts of legalese and jump straight to what changed, quarter over quarter.',
			'Support the project for $1/day and unlock full history plus early access to new features.'
		]
	},
	{
		eyebrow: 'EARLY-SUPPORTER SPECIAL',
		titleLead: 'Keep the synthesis',
		titleEm: 'running.',
		lines: [
			"As we catch up on existing filings, we're seeking early adopters to pitch in!",
			'Show your support — for just $1/day secure your access to advanced features and support ongoing symbology operations.'
		]
	}
];

/** Pick a hero-variant index for this request. `r` is injectable for testing. */
export function pickHeroVariant(r: number = Math.random()): number {
	return Math.floor(r * SUPPORT_HERO_VARIANTS.length) % SUPPORT_HERO_VARIANTS.length;
}
