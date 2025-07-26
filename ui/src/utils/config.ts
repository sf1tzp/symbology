// UI Configuration Module
// This module provides a synchronous interface to configuration
// that is loaded asynchronously from the backend API

import type { AppConfig } from './config-service';

// Default configuration for immediate use before API config loads
const defaultConfig = {
  env: import.meta.env.MODE || 'development',
  api: {
    host: import.meta.env.SYMBOLOGY_API_HOST || 'localhost',
    port: Number(import.meta.env.SYMBOLOGY_API_PORT) || 8000,
    get baseUrl() {
      const hostname = window.location.hostname;
      return `http://${hostname}:${this.port}/api`;
    },
    timeout: 30000,
  },
  logging: {
    level: import.meta.env.LOG_LEVEL || 'info',
    jsonFormat: import.meta.env.LOG_JSON_FORMAT === 'true' || false,
  },
};

// Runtime configuration will be set by the App component after loading from API
let runtimeConfig: AppConfig | null = null;

/**
 * Set runtime configuration loaded from the API
 */
export function setRuntimeConfig(config: AppConfig): void {
  runtimeConfig = config;
}

/**
 * Get current configuration (runtime if available, otherwise default)
 */
export const config = {
  get env() {
    return runtimeConfig?.environment || defaultConfig.env;
  },
  get api() {
    if (runtimeConfig) {
      return {
        host: new URL(runtimeConfig.api.baseUrl).hostname,
        port: Number(new URL(runtimeConfig.api.baseUrl).port),
        baseUrl: runtimeConfig.api.baseUrl,
        timeout: runtimeConfig.api.timeout,
      };
    }
    return defaultConfig.api;
  },
  get logging() {
    return runtimeConfig?.logging || defaultConfig.logging;
  },
};

export default config;
