import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { config } from '$lib/config';

export const GET: RequestHandler = async ({ params, fetch }) => {
    const { accession_number } = params;

    try {
        const apiUrl = `${config.api.baseUrl}/filings/${accession_number}/company`;
        console.log('Proxying company request to:', apiUrl);

        const response = await fetch(apiUrl);

        if (!response.ok) {
            console.error(`API request failed: ${response.status} ${response.statusText}`);
            return new Response(response.statusText, { status: response.status });
        }

        const data = await response.json();
        return json(data);
    } catch (error) {
        console.error('Error fetching filing company:', error);
        return new Response('Internal Server Error', { status: 500 });
    }
};
