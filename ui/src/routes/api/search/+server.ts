import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { unifiedSearch } from '$lib/server/db/search';

export const GET: RequestHandler = async ({ url }) => {
	const q = url.searchParams.get('q');
	if (!q) {
		return json({ results: [], total: 0, query: '' });
	}

	const entityTypes = url.searchParams.getAll('entity_types');
	const sic = url.searchParams.get('sic') || undefined;
	const formType = url.searchParams.get('form_type') || undefined;
	const documentType = url.searchParams.get('document_type') || undefined;
	const dateFrom = url.searchParams.get('date_from') || undefined;
	const dateTo = url.searchParams.get('date_to') || undefined;
	const limit = Math.min(Number(url.searchParams.get('limit')) || 20, 100);
	const offset = Number(url.searchParams.get('offset')) || 0;

	const response = await unifiedSearch(q, {
		entityTypes: entityTypes.length > 0 ? entityTypes : undefined,
		sic,
		formType,
		documentType,
		dateFrom,
		dateTo,
		limit,
		offset
	});

	return json(response);
};
