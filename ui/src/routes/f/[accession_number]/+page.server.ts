import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import {
	getFilingByAccession,
	getDocumentsByAccession,
	getCompanyByAccession
} from '$lib/server/db/filings';

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

	return {
		filing,
		documents,
		company,
		accession_number
	};
};
