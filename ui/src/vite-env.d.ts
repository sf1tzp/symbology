/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly ENV: string;
  readonly POSTGRES_USER: string;
  readonly POSTGRES_PASSWORD: string;
  readonly POSTGRES_DB: string;
  readonly POSTGRES_HOST: string;
  readonly POSTGRES_PORT: string;
  readonly PGADMIN_EMAIL: string;
  readonly PGADMIN_PASSWORD: string;
  readonly EDGAR_CONTACT: string;
  readonly OPENAI_HOST: string;
  readonly OPENAI_PORT: string;
  readonly OPENAI_DEFAULT_MODEL: string;
  readonly SYMBOLOGY_API_HOST: string;
  readonly SYMBOLOGY_API_PORT: string;
  readonly LOG_LEVEL: string;
  readonly LOG_JSON_FORMAT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
