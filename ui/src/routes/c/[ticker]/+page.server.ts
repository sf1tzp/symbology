import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getCurrentCompanyPageContent } from '$lib/server/db/page-content';
import { getFilingsTimeline } from '$lib/server/db/filings';
import { getFinancialComparison } from '$lib/server/db/financials';

export const load: PageServerLoad = async ({ params }) => {
	const ticker = params.ticker.toUpperCase();

	const company = await getCompanyByTicker(ticker);
	if (!company) {
		error(404, 'Company not found');
	}

	const [companyPageContent, timeline, financialComparison] = await Promise.all([
		getCurrentCompanyPageContent(company.id),
		getFilingsTimeline(ticker, 40, '10-K'),
		getFinancialComparison(ticker, undefined, 5, '10-K')
	]);

	// Companies without generated page content are not yet published — keep them
	// out of reach (they're also filtered from search/browse).
	if (!companyPageContent) {
		error(404, 'Company not found');
	}

	// Resolve the source filings (newest first) for the provenance list.
	const sourceIds = new Set(companyPageContent?.sourceFilingIds ?? []);
	const sourceFilings = timeline
		.filter((f) => sourceIds.has(f.id))
		.sort((a, b) =>
			(b.period_of_report ?? b.filing_date).localeCompare(a.period_of_report ?? a.filing_date)
		);

	return {
		ticker,
		company,
		companyPageContent,
		sourceFilings,
		filings: timeline,
		financialComparison
	};
};
