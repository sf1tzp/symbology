import type { PageLoad } from './$types';
import { getDocumentByAccessionAndHash } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
	const { accession_number, content_hash } = params;

	try {
		const document = await getDocumentByAccessionAndHash(accession_number, content_hash);

		if (!document) {
			throw new Error(`Document not found`);
		}

		return {
			document,
			accession_number,
			content_hash
		};
	} catch (error) {
		throw new Error(`Failed to load document: ${error}`);
	}
};
