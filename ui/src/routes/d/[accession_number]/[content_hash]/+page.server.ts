import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getFilingByAccession, getCompanyByAccession } from '$lib/server/db/filings';
import { getDocumentByAccessionAndHash } from '$lib/server/db/documents';
import { getCurrentDocumentPageContent } from '$lib/server/db/page-content';
import { getDiffSetsByRightFiling } from '$lib/server/db/diffs';

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

	// Page content + "what changed in this section vs the prior filing". Diffs are
	// keyed by the newer (right) filing; pick the set for this document's type.
	const [documentPageContent, priorDiffSets] = await Promise.all([
		getCurrentDocumentPageContent(document.id),
		getDiffSetsByRightFiling(filing.id)
	]);
	const sectionDiff =
		priorDiffSets.find((ds) => ds.documentType === document.document_type) ?? null;

	return {
		document,
		filing,
		company,
		documentPageContent,
		sectionDiff,
		accession_number,
		content_hash
	};
};
