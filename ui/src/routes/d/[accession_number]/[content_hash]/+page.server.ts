import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getDocumentByAccessionAndHash } from '$lib/server/db/documents';

export const load: PageServerLoad = async ({ params }) => {
	const { accession_number, content_hash } = params;

	const document = await getDocumentByAccessionAndHash(accession_number, content_hash);

	if (!document) {
		error(404, 'Document not found');
	}

	return {
		document,
		accession_number,
		content_hash
	};
};
