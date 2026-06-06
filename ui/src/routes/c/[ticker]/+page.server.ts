import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getCurrentCompanyPageContent, getCompanyPageForms } from '$lib/server/db/page-content';
import { getFilingsTimeline, getSourceFilingInputTokens } from '$lib/server/db/filings';
import { getFinancialComparison } from '$lib/server/db/financials';
import { getLatestChangeCards, companyHasDiffSets } from '$lib/server/db/diffs';

// Forms a company page can be published for, in display/default-priority order.
const PAGE_FORMS = ['10-K', '10-Q'];

export const load: PageServerLoad = async ({ params, url }) => {
	const ticker = params.ticker.toUpperCase();

	const company = await getCompanyByTicker(ticker);
	if (!company) {
		error(404, 'Company not found');
	}

	// Which forms this company has published page content for, and the one to
	// show: the requested ?form= if available, else 10-K, else 10-Q, else any.
	const publishedForms = await getCompanyPageForms(company.id);
	const availableForms = PAGE_FORMS.filter((f) => publishedForms.includes(f));
	const requestedForm = url.searchParams.get('form');
	const selectedForm =
		(requestedForm && availableForms.includes(requestedForm) && requestedForm) ||
		availableForms[0] ||
		'10-K';

	const [companyPageContent, timeline, changeCards, hasDiffSets] = await Promise.all([
		getCurrentCompanyPageContent(company.id, selectedForm),
		getFilingsTimeline(ticker, 80, ['10-K']), // '10-Q'
		getLatestChangeCards(company.id, 6, selectedForm),
		companyHasDiffSets(company.id)
	]);

	// Financials follow the selected form (e.g. quarterly figures on the 10-Q
	// page), but fall back to annual 10-K data when the form's comparison is
	// empty/inadequate so the stats strip never looks bare.
	let financialComparison = await getFinancialComparison(ticker, undefined, 5, selectedForm);
	if (selectedForm !== '10-K' && (financialComparison?.periods.length ?? 0) === 0) {
		financialComparison = await getFinancialComparison(ticker, undefined, 5, '10-K');
	}

	// A company is visible once it has computed diffs OR published page content.
	// Pending companies (diffs but no narrative yet) render a slimmed-down page;
	// only companies with neither are kept out of reach (matching search/browse).
	if (!companyPageContent && !hasDiffSets) {
		error(404, 'Company not found');
	}

	// Resolve the source filings (newest first) for the provenance list.
	const sourceIds = new Set(companyPageContent?.sourceFilingIds ?? []);
	const sourceFilings = timeline
		.filter((f) => sourceIds.has(f.id))
		.sort((a, b) =>
			(b.period_of_report ?? b.filing_date).localeCompare(a.period_of_report ?? a.filing_date)
		);

	// Total input-token volume the synthesis considered across its source filings.
	const sourceInputTokens = await getSourceFilingInputTokens([...sourceIds]);

	return {
		ticker,
		company,
		companyPageContent,
		sourceFilings,
		sourceInputTokens,
		filings: timeline,
		financialComparison,
		changeCards,
		selectedForm,
		availableForms
	};
};
