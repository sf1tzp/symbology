// UI Configuration Module
import { getLogger } from './logger';

const logger = getLogger('config');

// Environment type
const ENV = import.meta.env.ENV || 'development';

/**
 * Database settings interface
 */
interface DatabaseSettings {
  user: string;
  password: string;
  database: string;
  host: string;
  port: number;

  // Computed URL for database connection
  readonly url: string;
}

/**
 * PGAdmin settings interface
 */
interface PGAdminSettings {
  email: string;
  password: string;
}

/**
 * API settings interface
 */
interface ApiSettings {
  host: string;
  port: number;
  baseUrl: string;
  timeout: number;
}

/**
 * OpenAI settings interface
 */
interface OpenAISettings {
  host: string;
  port: string;
  defaultModel: string;
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
  database: DatabaseSettings;
  pgadmin: PGAdminSettings;
  api: ApiSettings;
  openai: OpenAISettings;
  logging: LoggingSettings;
}

// Create database settings with defaults
const databaseSettings: DatabaseSettings = {
  user: import.meta.env.POSTGRES_USER || 'postgres',
  password: import.meta.env.POSTGRES_PASSWORD || 'postgres',
  database: import.meta.env.POSTGRES_DB || 'symbology',
  host: import.meta.env.POSTGRES_HOST || 'localhost',
  port: Number(import.meta.env.POSTGRES_PORT) || 5432,

  // Getter for the computed URL
  get url() {
    // In practice, the frontend wouldn't directly connect to the database
    // but would use this URL for displaying connection info or similar purposes
    return `postgresql://${this.user}:${this.password}@${this.host}:${this.port}/${this.database}`;
  },
};

// Create PGAdmin settings with defaults
const pgadminSettings: PGAdminSettings = {
  email: import.meta.env.PGADMIN_EMAIL || 'dude@stev.lol',
  password: import.meta.env.PGADMIN_PASSWORD || 'postgres',
};

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

// Create OpenAI settings with defaults
const openaiSettings: OpenAISettings = {
  host: import.meta.env.OPENAI_HOST || '10.0.0.4',
  port: import.meta.env.OPENAI_PORT || '11434',
  defaultModel:
    import.meta.env.OPENAI_DEFAULT_MODEL || 'hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q6_K',
};

// Create logging settings with defaults
const loggingSettings: LoggingSettings = {
  level: import.meta.env.LOG_LEVEL || 'info',
  jsonFormat: import.meta.env.LOG_JSON_FORMAT === 'true' || false,
};

// Create and export the settings object
export const config: AppSettings = {
  env: ENV,
  database: databaseSettings,
  pgadmin: pgadminSettings,
  api: apiSettings,
  openai: openaiSettings,
  logging: loggingSettings,
};

// Log the current configuration (without sensitive data)
if (ENV !== 'production') {
  logger.debug('Application configuration loaded', {
    env: config.env,
    database: {
      host: config.database.host,
      port: config.database.port,
      database: config.database.database,
      // omit password for security
    },
    api: {
      host: config.api.host,
      port: config.api.port,
      baseUrl: config.api.baseUrl,
    },
    openai: {
      host: config.openai.host,
      port: config.openai.port,
      defaultModel: config.openai.defaultModel,
    },
    logging: config.logging,
  });
}

export default config;
