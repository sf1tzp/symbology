/**
 * API Type Re-exports & Utilities
 *
 * Re-exports component schemas from the generated OpenAPI types as named types,
 * plus runtime utilities for API interaction.
 */
import type { components } from './generated-api-types';

// Entity response types
export type CompanyResponse = components['schemas']['CompanyResponse'];
export type FilingResponse = components['schemas']['FilingResponse'];
export type DocumentResponse = components['schemas']['DocumentResponse'];
export type GeneratedContentResponse = components['schemas']['GeneratedContentResponse'];
export type ModelConfigResponse = components['schemas']['ModelConfigResponse'];
export type PromptResponse = components['schemas']['PromptResponse'];

// Company Group types
// Manually defined until API types are regenerated via `just -f ui/justfile generate-api-types`
export interface CompanyGroupResponse {
	id: string;
	name: string;
	slug: string;
	description: string | null;
	sic_codes: string[];
	member_count: number;
	created_at: string;
	updated_at: string;
	companies?: CompanyResponse[] | null;
	latest_analysis_summary?: string | null;
}

// Search types
export type SearchResponse = components['schemas']['SearchResponse'];
export type SearchResultItem = components['schemas']['SearchResultItem'];

// Job & Pipeline types
export type JobResponse = components['schemas']['JobResponse'];
export type PipelineRunResponse = components['schemas']['PipelineRunResponse'];
export type PipelineStatusResponse = components['schemas']['PipelineStatusResponse'];
export type CompanyPipelineStatus = components['schemas']['CompanyPipelineStatus'];

// Financial comparison types
export interface PeriodValue {
	date: string;
	value: number | null;
}

export interface PeriodChange {
	from_date: string;
	to_date: string;
	absolute: number | null;
	percent: number | null;
}

export interface FinancialLineItem {
	concept_name: string;
	description: string | null;
	labels: string[];
	values: PeriodValue[];
	changes: PeriodChange[];
}

export interface FinancialComparisonResponse {
	periods: string[];
	items: FinancialLineItem[];
}

// Timeline types for the filing-centric company page
export interface GeneratedContentSummaryResponse {
	id: string;
	content_hash: string | null;
	short_hash: string | null;
	description: string | null;
	document_type: string | null;
	summary: string | null;
	created_at: string;
}

export interface DocumentWithContentResponse {
	id: string;
	title: string;
	document_type: string | null;
	content_hash: string | null;
	short_hash: string | null;
	generated_content: GeneratedContentSummaryResponse[];
}

export interface FilingTimelineResponse {
	id: string;
	company_id: string;
	accession_number: string;
	form: string;
	filing_date: string;
	url: string | null;
	period_of_report: string | null;
	documents: DocumentWithContentResponse[];
}

/**
 * API Error Response
 */
export interface ApiError {
	detail: string;
}

/**
 * Type guard to check if a response is an ApiError
 */
export function isApiError(obj: unknown): obj is ApiError {
	return obj !== null && typeof obj === 'object' && 'detail' in obj;
}

/**
 * Helper to fetch data from the API with proper error handling
 */
export async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
	const response = await fetch(url, options);

	if (!response.ok) {
		const errorData = await response.json();
		throw new Error(errorData.detail || 'An error occurred');
	}

	return response.json() as Promise<T>;
}
