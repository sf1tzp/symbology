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
	company_group_id?: string | null;
	description?: string | null;
	document_type?: string | null;
	content_stage?: string | null;
	generation_depth?: number | null;
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

export interface PromptResponse {
	id: string;
	name: string;
	description?: string | null;
	role: string;
	content: string;
	content_hash?: string | null;
	short_hash?: string | null;
}

// One side (prior / current period) of a topic-diff synthesis. Reconstructed
// from the section diff's token ops; the source text the LLM summarised.
export interface DiffSourceSide {
	label: string;
	period: 'prior' | 'current';
	text: string;
	/** Deep link to the document page this side came from, when resolvable. */
	href?: string | null;
	filingForm?: string | null;
	filingDate?: string | null;
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
	// Which c/[ticker] content types exist for this company (set by the list API).
	has_10k_page?: boolean;
	has_10q_page?: boolean;
	has_diffs?: boolean;
}

export interface CompanyListResponse {
	companies: CompanyListItem[];
	total: number;
}

// Facet metadata for the /c faceted browse (GET /api/companies/facets).
export interface IndustryFacet {
	sic: string | null;
	sic_description: string;
	count: number;
}

export interface CompanyFacetsResponse {
	industries: IndustryFacet[];
}

// Filing list types (for the /f browse index)
export interface FilingListItem {
	id: string;
	accession_number: string;
	form: string;
	filing_date: string | null;
	period_of_report: string | null;
	company_ticker: string;
	company_name: string;
	company_display_name: string | null;
	/** Whether a synthesis (filing page content) has been generated for it. */
	has_analysis: boolean;
}

export interface FilingListResponse {
	filings: FilingListItem[];
	total: number;
}

// Synthesis list types (for the /s browse index)
export interface SynthesisListItem {
	short_hash: string;
	content_stage: string | null;
	form_type: string | null;
	generation_depth: number | null;
	created_at: string;
	/** Display name of the synthesis subject (company or group). */
	scope_label: string;
	/** Company ticker when the synthesis is company-scoped, else null. */
	scope_ticker: string | null;
}

export interface SynthesisListResponse {
	syntheses: SynthesisListItem[];
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

// Featured diff (landing-page "see exactly what changed" showcase) — one randomly
// chosen readable section diff, with just enough context to render a DiffView and
// deep-link into the company's full change report.
export interface LandingDiffOp {
	op: 'equal' | 'insert' | 'delete';
	text: string;
}

export interface LandingDiffFiling {
	form: string;
	filingDate: string | null;
	periodOfReport: string | null;
	accessionNumber: string;
	documentHash: string | null;
}

export interface LandingDiffShowcase {
	ticker: string;
	name: string;
	display_name: string | null;
	fiscal_year_end: string | null;
	documentType: string;
	sectionDiffId: string;
	sectionPath: string | null;
	heading: string | null;
	changeKind: string;
	/** Generated one-paragraph summary of the change (the editorial deck). */
	summary: string | null;
	ops: LandingDiffOp[];
	truncated: boolean;
	leftFiling: LandingDiffFiling | null;
	rightFiling: LandingDiffFiling | null;
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
