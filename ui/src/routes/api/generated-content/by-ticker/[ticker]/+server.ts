import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { config } from '$lib/config';

export const GET: RequestHandler = async ({ params, url, fetch }) => {
	const { ticker } = params;
	const limit = url.searchParams.get('limit') || '10';

	try {
		const apiUrl = `${config.api.baseUrl}/generated-content/by-ticker/${encodeURIComponent(ticker)}?limit=${limit}`;

		const response = await fetch(apiUrl);

		if (!response.ok) {
			const errorData = await response.json();
			return json(errorData, { status: response.status });
		}

		const data = await response.json();
		return json(data);
	} catch (error) {
		console.error('Error fetching generated content:', error);
		return json({ detail: 'Internal server error' }, { status: 500 });
	}
};
