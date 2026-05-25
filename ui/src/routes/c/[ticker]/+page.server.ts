import type { PageServerLoad } from './$types';
import { getCompanyByTicker } from '$lib/server/db/companies';
import {
	getAggregateSummariesByTicker,
	getAllGeneratedContentByTicker
} from '$lib/server/db/generated-content';
import { getFilingsTimeline } from '$lib/server/db/filings';
import { getFinancialComparison } from '$lib/server/db/financials';
import { getGroupsForCompany } from '$lib/server/db/groups';

export const load: PageServerLoad = async ({ params }) => {
	const ticker = params.ticker.toUpperCase();

	try {
		const [company, aggregateSummaries, filings, financialComparison, allGeneratedContent] =
			await Promise.all([
				getCompanyByTicker(ticker),
				getAggregateSummariesByTicker(ticker, 5),
				getFilingsTimeline(ticker, 20),
				getFinancialComparison(ticker),
				getAllGeneratedContentByTicker(ticker)
			]);

		const companyGroups = company ? await getGroupsForCompany(company.id) : [];

		return {
			ticker,
			company,
			aggregateSummaries,
			filings,
			financialComparison,
			allGeneratedContent,
			companyGroups
		};
	} catch (error) {
		console.error(`Failed to load data for ${ticker}:`, error);

		return {
			ticker,
			company: null,
			aggregateSummaries: [],
			filings: [],
			financialComparison: null,
			allGeneratedContent: [],
			companyGroups: [],
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};
