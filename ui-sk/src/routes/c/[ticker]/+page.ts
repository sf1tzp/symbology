import type { PageLoad } from './$types';
import type { CompanyResponse, GeneratedContentResponse, FilingResponse } from '$lib/generated-api-types';
import { getCompanyByTicker, getGeneratedContentByTicker, getFilingsByTicker } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
    const { ticker } = params;
    const upperTicker = ticker.toUpperCase();

    try {
        // Load company data, generated content, and filings in parallel
        const [company, generatedContent, filings] = await Promise.all([
            getCompanyByTicker(upperTicker),
            getGeneratedContentByTicker(upperTicker, 5),
            getFilingsByTicker(upperTicker, 5)
        ]);

        // If company not found, still return data but with null company
        return {
            ticker: upperTicker,
            company,
            generatedContent,
            filings
        };
    } catch (error) {
        console.error(`Failed to load data for ${ticker}:`, error);

        // Return partial data even if some API calls fail
        return {
            ticker: upperTicker,
            company: null,
            generatedContent: [],
            filings: [],
            error: error instanceof Error ? error.message : 'Unknown error'
        };
    }
};
