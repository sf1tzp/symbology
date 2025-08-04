import type { PageLoad } from './$types';
// Keep mock data as fallback
import { mockGeneratedContent, mockCompany, mockModelConfig, mockSourceDocuments } from '$lib/mockData';

export const load: PageLoad = async ({ params, fetch }) => {
    const { ticker, sha } = params;

    try {
        // Try to fetch real data from the API
        const [contentResponse, companyResponse] = await Promise.all([
            fetch(`/api/generated-content/by-ticker/${ticker}/${sha}`),
            fetch(`/api/companies/by-ticker/${ticker}`)
        ]);

        // If API calls succeed, use real data
        if (contentResponse.ok && companyResponse.ok) {
            const content = await contentResponse.json();
            const company = await companyResponse.json();

            // Fetch model config if available
            let modelConfig = null;
            if (content.model_config_id) {
                const modelConfigResponse = await fetch(`/api/model-configs/${content.model_config_id}`);
                if (modelConfigResponse.ok) {
                    modelConfig = await modelConfigResponse.json();
                }
            }

            // Fetch source documents if available
            let sources = [];
            if (content.source_document_ids && content.source_document_ids.length > 0) {
                const documentPromises = content.source_document_ids.map((docId: string) =>
                    fetch(`/api/documents/${docId}`).then(r => r.ok ? r.json() : null).catch(() => null)
                );
                const documents = await Promise.all(documentPromises);
                sources = documents.filter(doc => doc !== null);
            }

            return {
                content: {
                    ...content,
                    modelConfig,
                    sources
                },
                company,
                ticker,
                sha
            };
        }
    } catch (error) {
        console.warn('API call failed, falling back to mock data:', error);
    }

    // Fallback to mock data if API calls fail
    const content = {
        ...mockGeneratedContent,
        short_hash: sha,
        modelConfig: mockModelConfig,
        sources: mockSourceDocuments
    };

    const company = {
        ...mockCompany,
        tickers: [ticker]
    };

    return {
        content,
        company,
        ticker,
        sha
    };
};
