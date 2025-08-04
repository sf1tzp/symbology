import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
    const { edgar_id } = params;

    try {
        const [filing, documents, company] = await Promise.all([
            fetch(`/api/filings/${edgar_id}`).then(r => r.json()),
            fetch(`/api/filings/${edgar_id}/documents`).then(r => r.json()),
            fetch(`/api/filings/${edgar_id}/company`).then(r => r.json())
        ]);

        return {
            filing,
            documents,
            company,
            edgar_id
        };
    } catch (error) {
        throw new Error(`Failed to load filing: ${error}`);
    }
};
