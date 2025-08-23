import type { PageLoad } from './$types';
import { getFilingByAccession, getDocumentsByAccession, getCompanyByAccession } from '$lib/api';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params }) => {
	const { accession_number } = params;

	try {
		const [filing, documents, company] = await Promise.all([
			getFilingByAccession(accession_number),
			getDocumentsByAccession(accession_number),
			getCompanyByAccession(accession_number)
		]);

		// Ensure we have at least a filing to display the page
		if (!filing) {
			throw error(404, 'Filing not found');
		}

		return {
			filing,
			documents,
			company,
			accession_number
		};
	} catch (error) {
		throw new Error(`Failed to load filing: ${error}`);
	}
};
