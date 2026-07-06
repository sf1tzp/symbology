/**
 * Editorial status message shown in the operations hero.
 *
 * This is hand-curated, not derived from the live metrics — the numbers already
 * live in the dashboard below. Its job is to say, in the house voice, what the
 * pipeline is actually working on right now. Edit it whenever the focus shifts.
 *
 * Voice: measured, plain, analytical — the same register as the generated
 * change reports (see server/prompts/l2/change-report.md). State what's
 * happening; skip the adjectives and the restated counters.
 */
export interface StatusMessage {
	/** Short kicker — typically the date the note was written. */
	date: string;
	/** The headline: a user-friendly description of the current focus. */
	headline: string;
	/** A sentence or two of context, in the site's editorial voice. */
	body: string;
}

export const STATUS_MESSAGE: StatusMessage = {
	date: 'July 6',
	headline: 'Backfilling 10-K synthesis.',
	body:
		'We have ingested filings for the initial dataset and processed them for ' +
		'diffs. Now we are going through each company, looking back over the past ' +
		'five years for changes. We are reviewing our 10-Q content for quality and ' +
		'usefulness; existing content may change without notice. Thanks for your ' +
		'patience.'
};
