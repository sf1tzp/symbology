export const load = async ({ params, fetch }: { params: any; fetch: any }) => {
	const { accession_number, content_hash } = params;

	try {
		// Use the new API endpoint that accepts accession_number and content_hash
		const document = await fetch(
			`/api/documents/by-accession/${accession_number}/${content_hash}`
		).then((r: any) => {
			if (!r.ok) {
				throw new Error(`HTTP ${r.status}: ${r.statusText}`);
			}
			return r.json();
		});

		return {
			document,
			accession_number,
			content_hash
		};
	} catch (error) {
		throw new Error(`Failed to load document: ${error}`);
	}
};
