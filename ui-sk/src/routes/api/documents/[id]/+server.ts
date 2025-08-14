import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { config } from '$lib/config';

export const GET: RequestHandler = async ({ params, fetch }) => {
    const { id } = params;

    try {
        const apiUrl = `${config.api.baseUrl}/documents/${encodeURIComponent(id)}`;

        const response = await fetch(apiUrl);

        if (!response.ok) {
            const errorData = await response.json();
            return json(errorData, { status: response.status });
        }

        const data = await response.json();
        return json(data);
    } catch (error) {
        console.error('Error fetching document:', error);
        return json({ detail: 'Internal server error' }, { status: 500 });
    }
};
