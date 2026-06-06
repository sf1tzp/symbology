import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getCurrentCompanyPageContent } from '$lib/server/db/page-content';
import { getFilingsTimeline } from '$lib/server/db/filings';
import { getDiffSetChain } from '$lib/server/db/diffs';

export const load: PageServerLoad = async ({ params, url }) => {
	const ticker = params.ticker.toUpperCase();
	const documentType = params.document_type;
	// Keep the form the reader came from (10-K default, 10-Q via ?form=) so the
	// narrative report, diffs, and accent match the company page they left.
	const selectedForm = url.searchParams.get('form') === '10-Q' ? '10-Q' : '10-K';

	const company = await getCompanyByTicker(ticker);
	if (!company) {
		error(404, 'Company not found');
	}

	const companyPageContent = await getCurrentCompanyPageContent(company.id, selectedForm);

	// Chain of consecutive year-over-year diffs, oldest → newest. May be empty:
	// pending companies have diffs before any narrative, while boilerplate sections
	// (e.g. controls_procedures) get a narrative report but no section-level diff.
	const diffChain = await getDiffSetChain(company.id, documentType, 6, selectedForm);
	const diffSet = diffChain.at(-1) ?? null;

	// The narrative change report — present once the company page content has been
	// synthesised, and absent for pending companies.
	const changeReport =
		companyPageContent?.changeReports.find((c) => c.documentType === documentType) ?? null;

	// The view is reachable when EITHER side exists: diffs (pending company, no
	// narrative yet) or a narrative report (boilerplate section, no diff). 404 only
	// when this document type has neither.
	if (diffChain.length === 0 && !changeReport) {
		error(404, 'Change report not found');
	}

	const timeline = await getFilingsTimeline(ticker, 80, ['10-K', '10-Q']);
	const sourceIds = new Set(companyPageContent?.sourceFilingIds ?? []);
	const sourceFilings = timeline
		.filter((f) => sourceIds.has(f.id))
		.sort((a, b) =>
			(b.period_of_report ?? b.filing_date).localeCompare(a.period_of_report ?? a.filing_date)
		);

	return {
		ticker,
		documentType,
		company,
		changeReport,
		sourceFilings,
		diffSet,
		diffChain,
		selectedForm,
		createdAt: companyPageContent?.createdAt ?? null
	};
};
