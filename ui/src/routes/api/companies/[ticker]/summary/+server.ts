import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getCompanyByTicker } from '$lib/server/db/companies';

export const GET: RequestHandler = async ({ params }) => {
	const ticker = params.ticker.toUpperCase();
	const company = await getCompanyByTicker(ticker);

	if (!company) {
		throw error(404, 'Company not found');
	}

	return json({ summary: company.summary });
};
