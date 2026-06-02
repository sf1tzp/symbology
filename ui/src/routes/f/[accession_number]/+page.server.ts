import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import {
	getFilingByAccession,
	getDocumentsByAccession,
	getCompanyByAccession,
	getFilingsTimeline
} from '$lib/server/db/filings';
import { getCurrentFilingPageContent } from '$lib/server/db/page-content';

export const load: PageServerLoad = async ({ params }) => {
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

	const [filingPageContent, timeline] = await Promise.all([
		getCurrentFilingPageContent(filing.id),
		getFilingsTimeline(company.ticker, 10, '10-K')
	]);

	return {
		filing,
		documents,
		company,
		filingPageContent,
		accession_number,
		timeline
	};
};
