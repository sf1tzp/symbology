import type { PageLoad } from './$types';
import { getDocumentByAccessionAndHash } from '$lib/api';
import { error, isHttpError } from '@sveltejs/kit';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const { accession_number, content_hash } = params;

	try {
		const document = await getDocumentByAccessionAndHash(accession_number, content_hash);

		if (!document) {
			error(404, 'Document not found');
		}

		return {
			document,
			accession_number,
			content_hash
		};
	} catch (e) {
		if (isHttpError(e)) throw e;
		error(500, `Failed to load document: ${e}`);
	}
};
