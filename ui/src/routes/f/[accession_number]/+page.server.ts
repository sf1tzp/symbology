import type { Actions, PageServerLoad } from './$types';
import { error, fail } from '@sveltejs/kit';
import {
	getFilingByAccession,
	getDocumentsByAccession,
	getCompanyByAccession,
	getFilingsTimeline
} from '$lib/server/db/filings';
import { getCurrentFilingPageContent } from '$lib/server/db/page-content';
import { getDiffSetsByRightFiling } from '$lib/server/db/diffs';
import { filingAnalysisLock, viewerIsSupporter } from '$lib/server/gating';
import { prioritizeFilingAnalysis } from '$lib/server/db/jobs';

const yearOf = (iso: string | null | undefined): number | null => {
	if (!iso) return null;
	const y = new Date(iso).getFullYear();
	return Number.isFinite(y) ? y : null;
};

export const load: PageServerLoad = async ({ params, locals }) => {
	const { accession_number } = params;

	const [filing, documents, company] = await Promise.all([
		getFilingByAccession(accession_number),
		getDocumentsByAccession(accession_number),
		getCompanyByAccession(accession_number)
	]);

	if (!filing) {
		error(404, 'Filing not found');
	}

	if (!company) {
		error(404, 'Company not found');
	}

	const [filingPageContent, timeline, priorDiffSets, supporter] = await Promise.all([
		getCurrentFilingPageContent(filing.id),
		// Full periodic history (annual + quarterly) so the timeline matches the
		// company page. High limit so quarterlies (ordered period ASC) don't push
		// recent filings past the cutoff.
		getFilingsTimeline(company.ticker, 400, ['10-K', '10-Q']),
		getDiffSetsByRightFiling(filing.id),
		viewerIsSupporter(locals.user)
	]);

	// Gate generated analysis (10-Q, or 10-K beyond the free window) for free
	// viewers. Raw documents + diffs stay free, so only the page content is
	// withheld — and only when it actually exists.
	const analysisLock = filingPageContent
		? filingAnalysisLock(filing.form, filing.filing_date, supporter)
		: null;

	return {
		filing,
		documents,
		company,
		filingPageContent: analysisLock ? null : filingPageContent,
		analysisLock,
		accession_number,
		timeline,
		priorDiffSets
	};
};

export const actions: Actions = {
	/**
	 * Supporter perk: move this filing's queued analysis to the front of the
	 * worker queue. Supporters only — free users see the perk as a locked CTA and
	 * never reach this action.
	 */
	prioritize: async ({ params, locals }) => {
		if (!locals.user) return fail(401, { message: 'Sign in to prioritize analysis.' });
		if (!(await viewerIsSupporter(locals.user))) {
			return fail(403, { message: 'Prioritizing the queue is a supporter perk.' });
		}

		const [filing, company] = await Promise.all([
			getFilingByAccession(params.accession_number),
			getCompanyByAccession(params.accession_number)
		]);
		if (!filing || !company) return fail(404, { message: 'Filing not found.' });

		const years = [yearOf(filing.period_of_report), yearOf(filing.filing_date)].filter(
			(y): y is number => y !== null
		);
		const bumped = await prioritizeFilingAnalysis({
			accession: params.accession_number,
			ticker: company.ticker,
			form: filing.form,
			years
		});

		return {
			prioritized: true,
			// 0 means nothing was pending (already analysed, in-flight, or done).
			message:
				bumped > 0
					? 'Moved to the front of the queue — analysis will run next.'
					: 'This filing is already analysed or running; nothing to prioritize.'
		};
	}
};
