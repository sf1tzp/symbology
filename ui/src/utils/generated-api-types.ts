/**
 * GENERATED FILE - DO NOT EDIT
 * This file was automatically generated from the OpenAPI schema.
 * Run generate-api-types.js to regenerate.
 */

export interface CompanyResponse {
  /** Unique identifier for the company */
  id: string;
  /** Company CIK (Central Index Key) */
  cik?: any;
  /** Company name */
  name: string;
  /** Display name for the company */
  display_name?: any;
  /** Whether this is a company or not */
  is_company?: boolean;
  /** List of ticker symbols */
  tickers?: string[];
  /** List of exchanges where company is listed */
  exchanges?: string[];
  /** Standard Industrial Classification code */
  sic?: any;
  /** Description of the SIC code */
  sic_description?: any;
  /** Date of fiscal year end */
  fiscal_year_end?: any;
  /** Type of entity */
  entity_type?: any;
  /** Employer Identification Number */
  ein?: any;
  /** List of former company names */
  former_names?: object[];
}

export interface DocumentContentResponse {
  /** Unique identifier for the document */
  id: string;
  /** Document content (HTML) */
  content: string;
}

export interface DocumentResponse {
  /** Unique identifier for the document */
  id: string;
  /** ID of the filing this document belongs to */
  filing_id?: any;
  /** ID of the company this document belongs to */
  company_id: string;
  /** Name of the document */
  document_name: string;
  /** Text content of the document */
  content?: any;
}

export interface FilingResponse {
  /** Unique identifier for the filing */
  id: string;
  /** ID of the company this filing belongs to */
  company_id: string;
  /** SEC accession number */
  accession_number: string;
  /** SEC filing type (e.g., 10-K, 10-Q) */
  filing_type: string;
  /** Date the filing was submitted */
  filing_date: string;
  /** URL to the filing on SEC website */
  filing_url?: any;
  /** Period covered by the report */
  period_of_report?: any;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
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
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      // Try to parse error response as JSON
      let errorDetail: string;
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || `HTTP error ${response.status}`;
      } catch (e) {
        // If parsing fails, use status text
        errorDetail = `${response.status} ${response.statusText}`;
      }

      throw new Error(`Load failed: ${errorDetail}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    // Add network error handling
    if (error instanceof Error) {
      if (
        error.message.includes('Failed to fetch') ||
        error.message.includes('Network request failed')
      ) {
        throw new Error(
          `Network error: Cannot connect to API at ${url}. Make sure the API server is running and accessible on your network.`
        );
      }
    }
    throw error;
  }
}
