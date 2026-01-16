/**
 * API Configuration for SvelteKit App
 * Manages API endpoints and environment-specific settings
 */

import { env } from '$env/dynamic/public';

// Environment variables with defaults
const ENV = env.PUBLIC_ENVIRONMENT || 'development';
const API_HOST = env.PUBLIC_SYMBOLOGY_API_HOST || 'localhost';
const API_PORT = Number(env.PUBLIC_SYMBOLOGY_API_PORT) || 8000;

/**
 * Build API base URL based on environment
 */
function getApiBaseUrl(): string {
	// In production/staging, use HTTPS and the public API host
	if (ENV === 'production' || ENV === 'staging') {
		return `https://${API_HOST}`;
	}

	// In development, use local API server with HTTP
	return `http://${API_HOST}:${API_PORT}`;
}

export const config = {
	env: ENV,
	api: {
		baseUrl: getApiBaseUrl(),
		timeout: 30000
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
