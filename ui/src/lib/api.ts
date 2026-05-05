/**
 * API Service Module
 * Provides typed API functions using generated types
 */

import type {
	CompanyResponse,
	CompanyGroupResponse,
	FilingResponse,
	FilingTimelineResponse,
	DocumentResponse,
	GeneratedContentResponse,
	GeneratedContentSummaryResponse,
	ModelConfigResponse,
	SearchResponse,
	FinancialComparisonResponse
} from './api-types';
import { fetchApi, isApiError } from './api-types';
import { buildApiUrl, logApiCall, config } from './config';

/**
 * Search companies by name or ticker
 */
export async function searchCompanies(
	query: string,
	limit: number = 10
): Promise<CompanyResponse[]> {
	try {
		const url = buildApiUrl('/companies', {
			search: query,
			limit: limit.toString()
		});

		logApiCall('GET', url);

		const companies = await fetchApi<CompanyResponse[]>(url);
		return companies;
	} catch (error) {
		console.error('Error searching companies:', error);
		throw error;
	}
}

/**
 * Get company by ticker symbol
 */
export async function getCompanyByTicker(ticker: string): Promise<CompanyResponse | null> {
	try {
		const url = buildApiUrl(`/companies/by-ticker/${encodeURIComponent(ticker)}`);

		logApiCall('GET', url);

		const company = await fetchApi<CompanyResponse>(url);
		return company;
	} catch (error) {
		console.error(`Error fetching company by ticker ${ticker}:`, error);
		// Return null if company not found rather than throwing
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get all companies (with pagination)
 */
export async function getCompanies(
	skip: number = 0,
	limit: number = 50
): Promise<CompanyResponse[]> {
	try {
		const url = buildApiUrl('/companies', {
			skip: skip.toString(),
			limit: limit.toString()
		});

		logApiCall('GET', url);

		const companies = await fetchApi<CompanyResponse[]>(url);
		return companies;
	} catch (error) {
		console.error('Error fetching companies:', error);
		throw error;
	}
}

/**
 * Get generated content (AI analysis) for a company by ticker
 */
export async function getGeneratedContentByTicker(
	ticker: string,
	limit: number = 10
): Promise<GeneratedContentResponse[]> {
	try {
		const url = buildApiUrl(`/generated-content/by-ticker/${encodeURIComponent(ticker)}`, {
			limit: limit.toString()
		});

		logApiCall('GET', url);

		const generatedContent = await fetchApi<GeneratedContentResponse[]>(url);
		return generatedContent;
	} catch (error) {
		console.error(`Error fetching generated content for ticker ${ticker}:`, error);
		return []; // Return empty array rather than throwing for missing data
	}
}

/**
 * Get aggregate summaries for a company by ticker
 */
export async function getAggregateSummariesByTicker(
	ticker: string,
	limit: number = 10
): Promise<GeneratedContentResponse[]> {
	try {
		const url = buildApiUrl(
			`/generated-content/aggregate-summaries/by-ticker/${encodeURIComponent(ticker)}`,
			{
				limit: limit.toString()
			}
		);

		logApiCall('GET', url);

		const aggregateSummaries = await fetchApi<GeneratedContentResponse[]>(url);
		return aggregateSummaries;
	} catch (error) {
		console.error(`Error fetching aggregate summaries for ticker ${ticker}:`, error);
		return []; // Return empty array rather than throwing for missing data
	}
}

/**
 * Get all generated content for a company by ticker (lightweight listing)
 */
export async function getAllGeneratedContentByTicker(
	ticker: string,
	limit: number = 100
): Promise<GeneratedContentSummaryResponse[]> {
	try {
		const url = buildApiUrl(`/generated-content/all/by-ticker/${encodeURIComponent(ticker)}`, {
			limit: limit.toString()
		});

		logApiCall('GET', url);

		return await fetchApi<GeneratedContentSummaryResponse[]>(url);
	} catch (error) {
		console.error(`Error fetching all generated content for ticker ${ticker}:`, error);
		return [];
	}
}

/**
 * Get a specific generated content by ticker and hash
 */
export async function getGeneratedContentByTickerAndHash(
	ticker: string,
	hash: string
): Promise<GeneratedContentResponse | null> {
	try {
		const url = buildApiUrl(
			`/generated-content/by-ticker/${encodeURIComponent(ticker)}/${encodeURIComponent(hash)}`
		);

		logApiCall('GET', url);

		const generatedContent = await fetchApi<GeneratedContentResponse>(url);
		return generatedContent;
	} catch (error) {
		console.error(`Error fetching generated content for ticker ${ticker} and hash ${hash}:`, error);
		// Return null if content not found rather than throwing
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get model configuration by ID
 */
export async function getModelConfigById(id: string): Promise<ModelConfigResponse | null> {
	try {
		const url = buildApiUrl(`/model-configs/${encodeURIComponent(id)}`);

		logApiCall('GET', url);

		const modelConfig = await fetchApi<ModelConfigResponse>(url);
		return modelConfig;
	} catch (error) {
		console.error(`Error fetching model config ${id}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get document by ID
 */
export async function getDocumentById(id: string): Promise<DocumentResponse | null> {
	try {
		const url = buildApiUrl(`/documents/${encodeURIComponent(id)}`);

		logApiCall('GET', url);

		const document = await fetchApi<DocumentResponse>(url);
		return document;
	} catch (error) {
		console.error(`Error fetching document ${id}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get filings for a company by ticker
 */
export async function getFilingsByTicker(
	ticker: string,
	limit: number = 10
): Promise<FilingResponse[]> {
	try {
		const url = buildApiUrl(`/filings/by-ticker/${encodeURIComponent(ticker)}`, {
			limit: limit.toString()
		});

		logApiCall('GET', url);

		const filings = await fetchApi<FilingResponse[]>(url);
		// Sort by filing.period_of_report (most recent first)
		return filings.sort((a, b) => {
			const dateA = new Date(a.period_of_report || 0).getTime();
			const dateB = new Date(b.period_of_report || 0).getTime();
			return dateB - dateA;
		});
	} catch (error) {
		console.error(`Error fetching filings for ticker ${ticker}:`, error);
		return []; // Return empty array rather than throwing for missing data
	}
}

/**
 * Get filing timeline with nested documents and generated content for a company
 */
export async function getFilingsTimeline(
	ticker: string,
	limit: number = 20
): Promise<FilingTimelineResponse[]> {
	try {
		const url = buildApiUrl(`/filings/by-ticker/${encodeURIComponent(ticker)}/timeline`, {
			limit: limit.toString()
		});

		logApiCall('GET', url);

		return await fetchApi<FilingTimelineResponse[]>(url);
	} catch (error) {
		console.error(`Error fetching filing timeline for ticker ${ticker}:`, error);
		return [];
	}
}

/**
 * Get a specific generated content by ID
 */
export async function getGeneratedContentById(
	id: string
): Promise<GeneratedContentResponse | null> {
	try {
		const url = buildApiUrl(`/generated-content/${encodeURIComponent(id)}`);

		logApiCall('GET', url);

		const generatedContent = await fetchApi<GeneratedContentResponse>(url);
		return generatedContent;
	} catch (error) {
		console.error(`Error fetching generated content ${id}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get a specific filing by ID
 */
export async function getFilingById(id: string): Promise<FilingResponse | null> {
	try {
		const url = buildApiUrl(`/filings/${encodeURIComponent(id)}`);

		logApiCall('GET', url);

		const filing = await fetchApi<FilingResponse>(url);
		return filing;
	} catch (error) {
		console.error(`Error fetching filing ${id}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get documents for a filing
 */
export async function getDocumentsByFiling(filingId: string): Promise<DocumentResponse[]> {
	try {
		const url = buildApiUrl('/documents', {
			filing_id: filingId
		});

		logApiCall('GET', url);

		const documents = await fetchApi<DocumentResponse[]>(url);
		return documents;
	} catch (error) {
		console.error(`Error fetching documents for filing ${filingId}:`, error);
		return [];
	}
}

/**
 * Get filing by accession number
 */
export async function getFilingByAccession(
	accessionNumber: string
): Promise<FilingResponse | null> {
	try {
		const url = buildApiUrl(`/filings/${encodeURIComponent(accessionNumber)}`);

		logApiCall('GET', url);

		const filing = await fetchApi<FilingResponse>(url);
		return filing;
	} catch (error) {
		console.error(`Error fetching filing by accession ${accessionNumber}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get documents for a filing by accession number
 */
export async function getDocumentsByAccession(
	accessionNumber: string
): Promise<DocumentResponse[]> {
	try {
		const url = buildApiUrl(`/filings/${encodeURIComponent(accessionNumber)}/documents`);

		logApiCall('GET', url);

		const documents = await fetchApi<DocumentResponse[]>(url);
		return documents;
	} catch (error) {
		console.error(`Error fetching documents for accession ${accessionNumber}:`, error);
		return [];
	}
}

/**
 * Get company by filing accession number
 */
export async function getCompanyByAccession(
	accessionNumber: string
): Promise<CompanyResponse | null> {
	try {
		const url = buildApiUrl(`/filings/${encodeURIComponent(accessionNumber)}/company`);

		logApiCall('GET', url);

		const company = await fetchApi<CompanyResponse>(url);
		return company;
	} catch (error) {
		console.error(`Error fetching company for accession ${accessionNumber}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get document by accession number and content hash
 */
export async function getDocumentByAccessionAndHash(
	accessionNumber: string,
	contentHash: string
): Promise<DocumentResponse | null> {
	try {
		const url = buildApiUrl(
			`/documents/by-accession/${encodeURIComponent(accessionNumber)}/${encodeURIComponent(contentHash)}`
		);

		logApiCall('GET', url);

		const document = await fetchApi<DocumentResponse>(url);
		return document;
	} catch (error) {
		console.error(
			`Error fetching document for accession ${accessionNumber} and hash ${contentHash}:`,
			error
		);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get all company groups
 */
export async function getCompanyGroups(limit: number = 50): Promise<CompanyGroupResponse[]> {
	try {
		const params: Record<string, string> = { limit: limit.toString() };

		const url = buildApiUrl('/groups', params);
		logApiCall('GET', url);
		return await fetchApi<CompanyGroupResponse[]>(url);
	} catch (error) {
		console.error('Error fetching company groups:', error);
		return [];
	}
}

/**
 * Get a company group by slug
 */
export async function getCompanyGroupBySlug(slug: string): Promise<CompanyGroupResponse | null> {
	try {
		const url = buildApiUrl(`/groups/${encodeURIComponent(slug)}`);
		logApiCall('GET', url);
		return await fetchApi<CompanyGroupResponse>(url);
	} catch (error) {
		console.error(`Error fetching company group ${slug}:`, error);
		if (error instanceof Error && error.message.includes('404')) {
			return null;
		}
		throw error;
	}
}

/**
 * Get frontpage summary for a company group
 */
export async function getGroupFrontpageSummary(slug: string): Promise<string | null> {
	try {
		const url = buildApiUrl(`/groups/${encodeURIComponent(slug)}/frontpage-summary`);
		logApiCall('GET', url);
		const result = await fetchApi<{ summary: string }>(url);
		return result.summary;
	} catch (error) {
		console.error(`Error fetching group frontpage summary for ${slug}:`, error);
		return null;
	}
}

/**
 * Get analyses for a company group
 */
export async function getGroupAnalysis(
	slug: string,
	limit: number = 5
): Promise<GeneratedContentResponse[]> {
	try {
		const url = buildApiUrl(`/groups/${encodeURIComponent(slug)}/analysis`, {
			limit: limit.toString()
		});
		logApiCall('GET', url);
		return await fetchApi<GeneratedContentResponse[]>(url);
	} catch (error) {
		console.error(`Error fetching group analysis for ${slug}:`, error);
		return [];
	}
}

/**
 * Unified search across companies, filings, and generated content
 */
export async function search(
	query: string,
	options?: {
		entityTypes?: string[];
		sic?: string;
		formType?: string;
		documentType?: string;
		dateFrom?: string;
		dateTo?: string;
		limit?: number;
		offset?: number;
	}
): Promise<SearchResponse> {
	try {
		const params: Record<string, string> = { q: query };

		if (options?.sic) params.sic = options.sic;
		if (options?.formType) params.form_type = options.formType;
		if (options?.documentType) params.document_type = options.documentType;
		if (options?.dateFrom) params.date_from = options.dateFrom;
		if (options?.dateTo) params.date_to = options.dateTo;
		if (options?.limit) params.limit = options.limit.toString();
		if (options?.offset) params.offset = options.offset.toString();

		// Build URL with entity_types as repeated query params
		let url = buildApiUrl('/search', params);
		if (options?.entityTypes?.length) {
			const etParams = options.entityTypes
				.map((t) => `entity_types=${encodeURIComponent(t)}`)
				.join('&');
			url += (url.includes('?') ? '&' : '?') + etParams;
		}

		logApiCall('GET', url);

		return await fetchApi<SearchResponse>(url);
	} catch (error) {
		console.error('Error performing search:', error);
		throw error;
	}
}

/**
 * Get financial comparison data for a company
 */
export async function getFinancialComparison(
	ticker: string,
	statementType?: string,
	periods: number = 5
): Promise<FinancialComparisonResponse | null> {
	try {
		const params: Record<string, string> = { periods: periods.toString() };
		if (statementType) params.statement_type = statementType;

		const url = buildApiUrl(`/financials/${encodeURIComponent(ticker)}/comparison`, params);

		logApiCall('GET', url);

		return await fetchApi<FinancialComparisonResponse>(url);
	} catch (error) {
		console.error(`Error fetching financial comparison for ${ticker}:`, error);
		return null;
	}
}

/**
 * Error handler for API responses
 */
export function handleApiError(error: unknown): string {
	if (isApiError(error)) {
		return error.detail;
	}

	if (error instanceof Error) {
		return error.message;
	}

	return 'An unexpected error occurred';
}
