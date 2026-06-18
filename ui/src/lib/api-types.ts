/**
 * Shared response/DTO types for the UI.
 *
 * Hand-maintained shapes for the data the SvelteKit server layer
 * (`src/lib/server/db/*`) returns to pages and components. These were originally
 * generated from a Python API's OpenAPI schema; the UI has since moved to
 * SvelteKit server-side data loading, so the types are now defined here directly.
 */

// Entity response types
export interface CompanyResponse {
	id: string;
	name: string;
	display_name?: string | null;
	ticker: string;
	cik?: string | null;
	exchanges?: string[];
	sic?: string | null;
	sic_description?: string | null;
	fiscal_year_end?: string | null;
	former_names?: { name: string; date_changed: string }[];
	summary?: string | null;
}

export interface FilingResponse {
	id: string;
	company_id: string;
	accession_number: string;
	form: string;
	filing_date: string;
	url?: string | null;
	period_of_report: string | null;
}

export interface DocumentResponse {
	id: string;
	filing_id?: string | null;
	company_ticker: string;
	title: string;
	document_type: string;
	content?: string | null;
	filing?: FilingResponse | null;
	content_hash?: string | null;
	short_hash?: string | null;
}

export interface GeneratedContentResponse {
	id: string;
	content_hash?: string | null;
	short_hash?: string | null;
	company_id?: string | null;
	description?: string | null;
	document_type?: string | null;
	source_type: string;
	created_at: string;
	total_duration?: number | null;
	input_tokens?: number | null;
	output_tokens?: number | null;
	form_type?: string | null;
	warning?: string | null;
	content?: string | null;
	summary?: string | null;
	model_config_id?: string | null;
	system_prompt_id?: string | null;
	user_prompt_id?: string | null;
	source_document_ids?: string[];
	source_content_ids?: string[];
}

export interface ModelConfigResponse {
	id: string;
	model: string;
	created_at: string;
	options?: { [key: string]: unknown } | null;
	max_tokens?: number | null;
	temperature?: number | null;
	top_k?: number | null;
	top_p?: number | null;
}

// Company list types (enhanced with filing metadata)
export interface CompanyListItem {
	id: string;
	name: string;
	display_name: string | null;
	ticker: string;
	exchanges: string[];
	sic: string | null;
	sic_description: string | null;
	fiscal_year_end: string | null;
	former_names: Array<{ name: string; date_changed: string }>;
	summary: string | null;
	filing_count: number;
	last_filing_date: string | null;
	last_filing_form: string | null;
}

export interface CompanyListResponse {
	companies: CompanyListItem[];
	total: number;
}

// Featured company intro (landing-page carousel) — sourced from CompanyPageContent
export interface FeaturedCompanyIntro {
	ticker: string;
	name: string;
	display_name: string | null;
	sic_description: string | null;
	intro: string | null;
	source_form_type: string | null;
	source_filing_count: number;
	created_at: string | null;
}

// Company Group types
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
export interface SearchResultItem {
	entity_type: string;
	id: string;
	rank: number;
	headline?: string | null;
	title?: string | null;
	subtitle?: string | null;
	date_value?: string | null;
}

export interface SearchResponse {
	results?: SearchResultItem[];
	total: number;
	query: string;
}

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
	form_type: string | null;
	content_stage: string | null;
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
