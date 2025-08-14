import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { config } from '$lib/config';

export const GET: RequestHandler = async ({ params, fetch }) => {
    const { accession_number } = params;

    try {
        const response = await fetch(`${config.api.baseUrl}/filings/${accession_number}`);

        if (!response.ok) {
            return new Response(await response.text(), {
                status: response.status,
                statusText: response.statusText,
                headers: { 'Content-Type': 'application/json' }
            });
        }

        const data = await response.json();
        return json(data);
    } catch (error) {
        console.error('Error proxying filing request:', error);
        return new Response(JSON.stringify({ error: 'Failed to fetch filing' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
};
