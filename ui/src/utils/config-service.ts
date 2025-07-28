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
    // FIXME: Dynamic configuration needed
    const baseUrl = `https://api.symbology.lofi`;

    logger.info('config_load_start', { baseUrl });

    const response = await fetch(`${baseUrl}/api/config/config`, {
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

    logger.info('config_load_success', {
      environment: config.environment,
    });

    return config;
  } catch (error) {
    logger.warn('config_load_failed', { error });

    // FIXME: Dynamic configuration needed
    const baseUrl = `https://api.symbology.lofi`;

    // Fallback configuration for development or when API is unavailable
    const fallbackConfig: AppConfig = {
      environment: import.meta.env.MODE === 'development' ? 'development' : 'production',
      logging: {
        level: 'DEBUG',
        jsonFormat: false,
        enableBackendLogging: import.meta.env.MODE === 'development',
      },
      api: {
        baseUrl: `${baseUrl}/api`,
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
