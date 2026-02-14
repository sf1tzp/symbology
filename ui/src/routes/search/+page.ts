import type { PageLoad } from './$types';
import { search } from '$lib/api';

export const load: PageLoad = async ({ url }) => {
	const q = url.searchParams.get('q') || '';
	const entityTypes = url.searchParams.getAll('entity_types');
	const sic = url.searchParams.get('sic') || undefined;
	const formType = url.searchParams.get('form_type') || undefined;
	const documentType = url.searchParams.get('document_type') || undefined;
	const dateFrom = url.searchParams.get('date_from') || undefined;
	const dateTo = url.searchParams.get('date_to') || undefined;
	const limit = Number(url.searchParams.get('limit')) || 20;
	const offset = Number(url.searchParams.get('offset')) || 0;

	if (!q) {
		return {
			query: '',
			results: [],
			total: 0,
			limit,
			offset,
			filters: { entityTypes, sic, formType, documentType, dateFrom, dateTo }
		};
	}

	try {
		const response = await search(q, {
			entityTypes: entityTypes.length > 0 ? entityTypes : undefined,
			sic,
			formType,
			documentType,
			dateFrom,
			dateTo,
			limit,
			offset
		});

		return {
			query: q,
			results: response.results ?? [],
			total: response.total,
			limit,
			offset,
			filters: { entityTypes, sic, formType, documentType, dateFrom, dateTo }
		};
	} catch (error) {
		console.error('Search failed:', error);
		return {
			query: q,
			results: [],
			total: 0,
			limit,
			offset,
			filters: { entityTypes, sic, formType, documentType, dateFrom, dateTo },
			error: error instanceof Error ? error.message : 'Search failed'
		};
	}
};
