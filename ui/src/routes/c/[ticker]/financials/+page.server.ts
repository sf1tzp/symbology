import type { PageServerLoad } from './$types';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getFinancialComparison } from '$lib/server/db/financials';
import { getFilingsTimeline } from '$lib/server/db/filings';

export const load: PageServerLoad = async ({ params }) => {
	const ticker = params.ticker.toUpperCase();

	try {
		const [company, financialComparison, filings] = await Promise.all([
			getCompanyByTicker(ticker),
			getFinancialComparison(ticker, undefined, 20, '10-K'),
			getFilingsTimeline(ticker, 5)
		]);

		return {
			ticker,
			company,
			financialComparison,
			filings: filings || []
		};
	} catch (error) {
		console.error(`Failed to load financials for ${ticker}:`, error);

		return {
			ticker,
			company: null,
			financialComparison: null,
			filings: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
