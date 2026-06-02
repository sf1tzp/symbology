import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getFilingByAccession, getCompanyByAccession } from '$lib/server/db/filings';
import { getDocumentByAccessionAndHash } from '$lib/server/db/documents';
import { getCurrentDocumentPageContent } from '$lib/server/db/page-content';

export const load: PageServerLoad = async ({ params }) => {
	const { accession_number, content_hash } = params;

	const [document, filing, company] = await Promise.all([
		getDocumentByAccessionAndHash(accession_number, content_hash),
		getFilingByAccession(accession_number),
		getCompanyByAccession(accession_number)
	]);

	if (!filing) {
		error(404, 'Filing not found');
	}

	if (!document) {
		error(404, 'Document not found');
	}

	const documentPageContent = await getCurrentDocumentPageContent(document.id);

	return {
		document,
		filing,
		company,
		documentPageContent,
		accession_number,
		content_hash
	};
};
