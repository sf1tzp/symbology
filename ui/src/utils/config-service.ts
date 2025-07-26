import { getLogger } from './logger';

const logger = getLogger('ConfigService');

export interface AppConfig {
  environment: string;
  logging: {
    level: string;
    jsonFormat: boolean;
    enableBackendLogging: boolean;
  };
  api: {
    baseUrl: string;
    timeout: number;
  };
  features: {
    enableAnalytics: boolean;
    enableDebugMode: boolean;
  };
}

let configCache: AppConfig | null = null;

/**
 * Fetch application configuration from the backend API
 */
export async function loadConfig(): Promise<AppConfig> {
  if (configCache) {
    return configCache;
  }

  try {
    // Build the config URL based on current location
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.hostname === 'localhost' ? '8000' : '8000';
    const configUrl = `${protocol}//${hostname}:${port}/api/config/config`;

    logger.info('Loading configuration from API', { configUrl });

    const response = await fetch(configUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-cache',
    });

    if (!response.ok) {
      throw new Error(`Config API returned ${response.status}: ${response.statusText}`);
    }

    const config: AppConfig = await response.json();
    configCache = config;

    logger.info('Configuration loaded successfully', {
      environment: config.environment,
      enableBackendLogging: config.logging.enableBackendLogging,
    });

    return config;
  } catch (error) {
    logger.warn('Failed to load config from API, using fallback', { error });

    // Fallback configuration for development or when API is unavailable
    const fallbackConfig: AppConfig = {
      environment: import.meta.env.MODE === 'development' ? 'development' : 'production',
      logging: {
        level: 'DEBUG',
        jsonFormat: false,
        enableBackendLogging: import.meta.env.MODE === 'development',
      },
      api: {
        baseUrl: `http://${window.location.hostname}:8000/api`,
        timeout: 30000,
      },
      features: {
        enableAnalytics: false,
        enableDebugMode: import.meta.env.MODE === 'development',
      },
    };

    configCache = fallbackConfig;
    return fallbackConfig;
  }
}

/**
 * Get cached configuration (must call loadConfig first)
 */
export function getConfig(): AppConfig {
  if (!configCache) {
    throw new Error('Configuration not loaded. Call loadConfig() first.');
  }
  return configCache;
}

/**
 * Clear configuration cache (useful for testing)
 */
export function clearConfig(): void {
  configCache = null;
}
