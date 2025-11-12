/**
 * GENERATED FILE - DO NOT EDIT
 * This file was automatically generated from the OpenAPI schema.
 * Run generate-api-types.js to regenerate.
 */

export interface CompanyResponse {
	/** Unique identifier for the company */
	id: string;
	/** Company name */
	name: string;
	/** Display name for the company */
	display_name?: any;
	/** Company tikcer symbol */
	ticker: string;
	/** List of exchanges where company is listed */
	exchanges?: string[];
	/** Standard Industrial Classification code */
	sic?: any;
	/** Description of the SIC code */
	sic_description?: any;
	/** Date of fiscal year end */
	fiscal_year_end?: any;
	/** List of former company names */
	former_names?: object[];
	/** Generated company summary based on aggregated analysis */
	summary?: any;
}

export interface DocumentResponse {
	/** Unique identifier for the document */
	id: string;
	/** ID of the filing this document belongs to */
	filing_id?: any;
	/** ID of the company this document belongs to */
	company_ticker: string;
	/** Name of the document */
	title: string;
	/** Type of the document */
	document_type: string;
	/** Text content of the document */
	content?: any;
	/** Filing information including SEC URL */
	filing?: any;
	/** SHA256 hash of the content */
	content_hash?: any;
	/** Shortened version of content hash for URLs */
	short_hash?: any;
}

export interface FilingResponse {
	/** Unique identifier for the filing */
	id: string;
	/** ID of the company this filing belongs to */
	company_id: string;
	/** SEC accession number */
	accession_number: string;
	/** SEC filing type (e.g., 10-K, 10-Q) */
	form: string;
	/** Date the filing was submitted */
	filing_date: string;
	/** URL to the filing on SEC website */
	url?: any;
	/** Period covered by the report */
	period_of_report?: any;
}

export interface GeneratedContentResponse {
	/** Unique identifier for the generated content */
	id: string;
	/** SHA256 hash of the content */
	content_hash?: any;
	/** Shortened hash for URLs (first 12 characters) */
	short_hash?: any;
	/** ID of the company this content belongs to */
	company_id?: any;
	/** Type of document (e.g., MDA, RISK_FACTORS, DESCRIPTION) */
	document_type?: any;
	/** Type of sources used (documents, generated_content, both) */
	source_type: string;
	/** Timestamp when the content was created */
	created_at: string;
	/** Total duration of content generation in seconds */
	total_duration?: any;
	/** Warning message if any issues occurred during generation */
	warning?: any;
	/** The actual AI-generated content */
	content?: any;
	/** Generated summary of the content */
	summary?: any;
	/** ID of the model configuration used */
	model_config_id?: any;
	/** ID of the system prompt used */
	system_prompt_id?: any;
	/** ID of the user prompt used */
	user_prompt_id?: any;
	/** List of source document IDs */
	source_document_ids?: string[];
	/** List of source content IDs */
	source_content_ids?: string[];
}

export interface HTTPValidationError {
	detail?: ValidationError[];
}

export interface ModelConfigResponse {
	/** Unique identifier for the model config */
	id: string;
	/** Model name */
	model: string;
	/** Timestamp when the config was created */
	created_at: string;
	/** Ollama options as JSON */
	options?: any;
	/** Context window size */
	num_ctx?: any;
	/** Temperature parameter */
	temperature?: any;
	/** Top-k parameter */
	top_k?: any;
	/** Top-p parameter */
	top_p?: any;
	/** Random seed */
	seed?: any;
	/** Number of tokens to predict */
	num_predict?: any;
	/** Number of GPUs to use */
	num_gpu?: any;
}

export interface PromptResponse {
	/** Unique identifier for the prompt */
	id: string;
	/** Name of the prompt */
	name: string;
	/** Description of the prompt */
	description?: any;
	/** Role of the prompt (system, assistant, user) */
	role: string;
	/** Prompt content text */
	content: string;
}

export interface ValidationError {
	loc: any[];
	msg: string;
	type: string;
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
export function isApiError(obj: any): obj is ApiError {
	return obj && typeof obj === 'object' && 'detail' in obj;
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
