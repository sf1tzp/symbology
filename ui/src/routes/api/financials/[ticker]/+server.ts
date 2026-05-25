import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getFinancialComparison } from '$lib/server/db/financials';

export const GET: RequestHandler = async ({ params, url }) => {
	const { ticker } = params;
	const statementType = url.searchParams.get('statement_type') || undefined;
	const periods = Number(url.searchParams.get('periods')) || 5;

	const result = await getFinancialComparison(ticker, statementType, periods);

	if (!result) {
		return json({ periods: [], items: [] });
	}

	return json(result);
};
