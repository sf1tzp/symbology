import type { PageLoad } from './$types';
import {
	getCompanyByTicker,
	getAggregateSummariesByTicker,
	getFilingsByTicker,
	getFinancialComparison
} from '$lib/api';

export const load: PageLoad = async ({ params }) => {
	const { ticker } = params;
	const upperTicker = ticker.toUpperCase();

	try {
		// Load company data, generated content, filings, and financial data in parallel
		const [company, generatedContent, filings, financialComparison] = await Promise.all([
			getCompanyByTicker(upperTicker),
			getAggregateSummariesByTicker(upperTicker, 5),
			getFilingsByTicker(upperTicker, 5),
			getFinancialComparison(upperTicker)
		]);

		// If company not found, still return data but with null company
		return {
			ticker: upperTicker,
			company,
			generatedContent,
			filings,
			financialComparison
		};
	} catch (error) {
		console.error(`Failed to load data for ${ticker}:`, error);

		// Return partial data even if some API calls fail
		return {
			ticker: upperTicker,
			company: null,
			generatedContent: [],
			filings: [],
			financialComparison: null,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
