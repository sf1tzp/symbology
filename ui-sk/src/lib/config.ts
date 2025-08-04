/**
 * API Configuration for SvelteKit App
 * Manages API endpoints and environment-specific settings
 */

// Environment variables with defaults
const ENV = import.meta.env.MODE || 'development';
const API_HOST = import.meta.env.SYMBOLOGY_API_HOST || '10.0.0.3';
const API_PORT = Number(import.meta.env.SYMBOLOGY_API_PORT) || 8000;

/**
 * Build API base URL based on environment
 */
function getApiBaseUrl(): string {
    // In production, use the configured API host
    if (ENV === 'production') {
        return `https://${API_HOST}/api`;
    }

    // In development, use local API server
    return `http://${API_HOST}:${API_PORT}/api`;
}

export const config = {
    env: ENV,
    api: {
        baseUrl: getApiBaseUrl(),
        timeout: 30000,
        endpoints: {
            companies: '/companies',
            companyByTicker: '/companies/by-ticker',
            aggregates: '/aggregates',
            aggregatesByTicker: '/aggregates/by-ticker',
            filings: '/filings',
            filingsByTicker: '/filings/by-ticker',
            completions: '/completions',
            documents: '/documents'
        }
    },
    logging: {
        level: import.meta.env.LOG_LEVEL || 'info',
        enabled: ENV !== 'production'
    }
};

/**
 * Build full API URL for an endpoint
 */
export function buildApiUrl(endpoint: string, params?: Record<string, string>): string {
    let url = `${config.api.baseUrl}${endpoint}`;

    if (params) {
        const searchParams = new URLSearchParams(params);
        url += `?${searchParams.toString()}`;
    }

    return url;
}

/**
 * Log API calls in development
 */
export function logApiCall(method: string, url: string, data?: any): void {
    if (config.logging.enabled) {
        console.log(`[API] ${method} ${url}`, data || '');
    }
}
