import type { PageLoad } from './$types';
import { getFilingByAccession, getDocumentsByAccession, getCompanyByAccession } from '$lib/api';
import { error, isHttpError } from '@sveltejs/kit';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const { accession_number } = params;

	try {
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
	} catch (e) {
		if (isHttpError(e)) throw e;
		error(500, `Failed to load filing: ${e}`);
	}
};
