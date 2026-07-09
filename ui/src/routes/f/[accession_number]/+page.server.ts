import type { Actions, PageServerLoad } from './$types';
import { error, fail } from '@sveltejs/kit';
import {
	getFilingByAccession,
	getDocumentsByAccession,
	getCompanyByAccession,
	getFilingsTimeline
} from '$lib/server/db/filings';
import { getCurrentFilingPageContent, toTeaser } from '$lib/server/db/page-content';
import { getDiffSetsByRightFiling } from '$lib/server/db/diffs';
import { filingAnalysisLock, viewerIsSupporter, type LockReason } from '$lib/server/gating';
import { checkCompanyView } from '$lib/server/meter';
import { prioritizeFilingAnalysis } from '$lib/server/db/jobs';

const yearOf = (iso: string | null | undefined): number | null => {
	if (!iso) return null;
	const y = new Date(iso).getFullYear();
	return Number.isFinite(y) ? y : null;
};

export const load: PageServerLoad = async ({ params, locals, cookies }) => {
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

	// Two gates, only when there's synthesis to withhold (raw documents + diffs
	// stay free regardless). The anonymous view meter comes first: a signed-out
	// guest past their free-company budget sees a sign-up wall with the intro as
	// a teaser. Otherwise the supporter history perk applies (>5y 10-K), which
	// withholds the synthesis entirely.
	const meter = checkCompanyView({
		cookies,
		user: locals.user,
		companyId: company.id,
		hasContent: !!filingPageContent
	});
	const analysisLock: LockReason | null = !filingPageContent
		? null
		: meter.metered
			? 'meter'
			: filingAnalysisLock(filing.form, filing.filing_date, supporter);

	return {
		filing,
		documents,
		company,
		// Metered guests keep the intro teaser; the history lock withholds fully.
		filingPageContent:
			analysisLock === 'meter' && filingPageContent
				? toTeaser(filingPageContent)
				: analysisLock
					? null
					: filingPageContent,
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
