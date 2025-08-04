import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
    const { edgar_id } = params;

    try {
        const [document, filing, company] = await Promise.all([
            fetch(`/api/documents/${edgar_id}`).then(r => r.json()),
            fetch(`/api/documents/${edgar_id}/filing`).then(r => r.json()),
            fetch(`/api/documents/${edgar_id}/company`).then(r => r.json())
        ]);

        return {
            document,
            filing,
            company,
            edgar_id
        };
    } catch (error) {
        throw new Error(`Failed to load document: ${error}`);
    }
};
