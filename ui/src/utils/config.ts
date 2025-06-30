// UI Configuration Module

const ENV = import.meta.env.ENV || 'development';

/*
 /!**
  * API settings interface
  *!/
 */
interface ApiSettings {
  host: string;
  port: number;
  baseUrl: string;
  timeout: number;
}

/**
 * Logging settings interface
 */
interface LoggingSettings {
  level: string;
  jsonFormat: boolean;
}

/**
 * Main application settings
 */
interface AppSettings {
  env: string;
  api: ApiSettings;
  logging: LoggingSettings;
}

// Create API settings with defaults
const apiSettings: ApiSettings = {
  host: import.meta.env.SYMBOLOGY_API_HOST || 'localhost',
  port: Number(import.meta.env.SYMBOLOGY_API_PORT) || 8000,

  // Build baseUrl dynamically to support cross-device access
  get baseUrl() {
    // In development mode, use the current device's hostname or IP
    if (ENV === 'development') {
      // Get the current window's hostname
      const hostname = window.location.hostname;
      return `http://${hostname}:${this.port}/api`;
    }
    return `http://${this.host}:${this.port}/api`;
  },
  timeout: 30000,
};

// Create logging settings with defaults
const loggingSettings: LoggingSettings = {
  level: import.meta.env.LOG_LEVEL || 'info',
  jsonFormat: import.meta.env.LOG_JSON_FORMAT === 'true' || false,
};

// Create and export the settings object
export const config: AppSettings = {
  env: ENV,
  api: apiSettings,
  logging: loggingSettings,
};

export default config;
