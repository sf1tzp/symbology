import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
    const { accession_number } = params;

    try {
        const [filing, documents, company] = await Promise.all([
            fetch(`/api/filings/${accession_number}`).then(r => r.json()),
            fetch(`/api/filings/${accession_number}/documents`).then(r => r.json()),
            fetch(`/api/filings/${accession_number}/company`).then(r => r.json())
        ]);

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
