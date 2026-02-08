import type { PageLoad } from './$types';
import {
	getCompanyByTicker,
	getAggregateSummariesByTicker,
	getFilingsTimeline,
	getFinancialComparison
} from '$lib/api';

export const load: PageLoad = async ({ params }) => {
	const { ticker } = params;
	const upperTicker = ticker.toUpperCase();

	try {
		// Load company data, aggregate summaries, filing timeline, and financial data in parallel
		const [company, aggregateSummaries, filings, financialComparison] = await Promise.all([
			getCompanyByTicker(upperTicker),
			getAggregateSummariesByTicker(upperTicker, 5),
			getFilingsTimeline(upperTicker, 20),
			getFinancialComparison(upperTicker)
		]);

		return {
			ticker: upperTicker,
			company,
			aggregateSummaries,
			filings,
			financialComparison
		};
	} catch (error) {
		console.error(`Failed to load data for ${ticker}:`, error);

		return {
			ticker: upperTicker,
			company: null,
			aggregateSummaries: [],
			filings: [],
			financialComparison: null,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
