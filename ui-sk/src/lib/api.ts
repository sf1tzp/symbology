/**
 * API Service Module
 * Provides typed API functions using generated types
 */

import type {
    CompanyResponse,
    AggregateResponse,
    FilingResponse,
    CompletionResponse,
    DocumentResponse
} from './generated-api-types';
import { fetchApi, isApiError } from './generated-api-types';
import { buildApiUrl, logApiCall } from './config';

/**
 * Search companies by name or ticker
 */
export async function searchCompanies(query: string, limit: number = 10): Promise<CompanyResponse[]> {
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
export async function getCompanies(skip: number = 0, limit: number = 50): Promise<CompanyResponse[]> {
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
 * Get aggregates (AI analysis) for a company by ticker
 */
export async function getAggregatesByTicker(ticker: string, limit: number = 10): Promise<AggregateResponse[]> {
    try {
        const url = buildApiUrl(`/aggregates/by-ticker/${encodeURIComponent(ticker)}`, {
            limit: limit.toString()
        });

        logApiCall('GET', url);

        const aggregates = await fetchApi<AggregateResponse[]>(url);
        return aggregates;
    } catch (error) {
        console.error(`Error fetching aggregates for ticker ${ticker}:`, error);
        return []; // Return empty array rather than throwing for missing data
    }
}

/**
 * Get filings for a company by ticker
 */
export async function getFilingsByTicker(ticker: string, limit: number = 10): Promise<FilingResponse[]> {
    try {
        const url = buildApiUrl(`/filings/by-ticker/${encodeURIComponent(ticker)}`, {
            limit: limit.toString()
        });

        logApiCall('GET', url);

        const filings = await fetchApi<FilingResponse[]>(url);
        return filings;
    } catch (error) {
        console.error(`Error fetching filings for ticker ${ticker}:`, error);
        return []; // Return empty array rather than throwing for missing data
    }
}

/**
 * Get a specific aggregate by ID
 */
export async function getAggregateById(id: string): Promise<AggregateResponse | null> {
    try {
        const url = buildApiUrl(`/aggregates/${encodeURIComponent(id)}`);

        logApiCall('GET', url);

        const aggregate = await fetchApi<AggregateResponse>(url);
        return aggregate;
    } catch (error) {
        console.error(`Error fetching aggregate ${id}:`, error);
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
 * Get completions (AI generated content) by source documents
 */
export async function getCompletionsByDocuments(documentIds: string[]): Promise<CompletionResponse[]> {
    try {
        const url = buildApiUrl('/completions', {
            document_ids: documentIds.join(',')
        });

        logApiCall('GET', url);

        const completions = await fetchApi<CompletionResponse[]>(url);
        return completions;
    } catch (error) {
        console.error('Error fetching completions:', error);
        return [];
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
