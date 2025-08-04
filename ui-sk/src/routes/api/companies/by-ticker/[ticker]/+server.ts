import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
    const { ticker } = params;

    try {
        // Proxy to your existing API
        const response = await fetch(`${process.env.API_BASE_URL}/api/companies/by-ticker/${ticker}`);

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}`);
        }

        const data = await response.json();
        return json(data);
    } catch (error) {
        console.error(`Failed to fetch company data for ${ticker}:`, error);
        return json({ error: 'Failed to fetch company data' }, { status: 500 });
    }
};
