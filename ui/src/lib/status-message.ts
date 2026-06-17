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
	date: 'June 8',
	headline: 'Pre-loading filing content, embeddings, and diffs.',
	body:
		'Ahead of launch we are seeding the corpus: ingesting Fortune 500 filings, ' +
		'embedding each section for semantic search, and precomputing the ' +
		'year-over-year diffs that drive the change reports. The queues below will ' +
		'run hot until the backlog drains.'
};
