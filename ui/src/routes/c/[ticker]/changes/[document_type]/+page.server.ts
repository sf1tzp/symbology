import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getCurrentCompanyPageContent } from '$lib/server/db/page-content';
import { getFilingsTimeline } from '$lib/server/db/filings';
import { getDiffSetChain } from '$lib/server/db/diffs';

export const load: PageServerLoad = async ({ params }) => {
	const ticker = params.ticker.toUpperCase();
	const documentType = params.document_type;

	const company = await getCompanyByTicker(ticker);
	if (!company) {
		error(404, 'Company not found');
	}

	const companyPageContent = await getCurrentCompanyPageContent(company.id);
	const changeReport = companyPageContent?.changeReports.find(
		(c) => c.documentType === documentType
	);
	if (!changeReport) {
		error(404, 'Change report not found');
	}

	const timeline = await getFilingsTimeline(ticker, 40, '10-K');
	const sourceIds = new Set(companyPageContent?.sourceFilingIds ?? []);
	const sourceFilings = timeline
		.filter((f) => sourceIds.has(f.id))
		.sort((a, b) =>
			(b.period_of_report ?? b.filing_date).localeCompare(a.period_of_report ?? a.filing_date)
		);

	// Chain of consecutive year-over-year diffs, oldest → newest (may be empty if
	// no diffs computed yet). The newest pairing drives the masthead counts.
	const diffChain = await getDiffSetChain(company.id, documentType);
	const diffSet = diffChain.at(-1) ?? null;

	return {
		ticker,
		documentType,
		company,
		changeReport,
		sourceFilings,
		diffSet,
		diffChain,
		createdAt: companyPageContent?.createdAt ?? null
	};
};
