import type { PageServerLoad } from './$types';
import { getCompanyByTicker } from '$lib/server/db/companies';
import { getFinancialComparison } from '$lib/server/db/financials';
import { getFilingsTimeline } from '$lib/server/db/filings';

export const load: PageServerLoad = async ({ params, url }) => {
	const ticker = params.ticker.toUpperCase();
	// Follow the selected form (e.g. quarterly figures from the 10-Q page), with
	// an annual fallback when that form has no financial data.
	const selectedForm = url.searchParams.get('form') === '10-Q' ? '10-Q' : '10-K';

	try {
		const [company, formFinancials, filings] = await Promise.all([
			getCompanyByTicker(ticker),
			getFinancialComparison(ticker, undefined, 20, selectedForm),
			getFilingsTimeline(ticker, 5)
		]);

		const financialComparison =
			selectedForm !== '10-K' && (formFinancials?.periods.length ?? 0) === 0
				? await getFinancialComparison(ticker, undefined, 20, '10-K')
				: formFinancials;

		return {
			ticker,
			company,
			financialComparison,
			filings: filings || [],
			selectedForm
		};
	} catch (error) {
		console.error(`Failed to load financials for ${ticker}:`, error);

		return {
			ticker,
			company: null,
			financialComparison: null,
			filings: [],
			selectedForm,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
