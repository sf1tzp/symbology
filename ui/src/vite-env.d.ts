/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly ENV: string;
  readonly EDGAR_CONTACT: string;
  readonly SYMBOLOGY_API_HOST: string;
  readonly SYMBOLOGY_API_PORT: string;
  readonly LOG_LEVEL: string;
  readonly LOG_JSON_FORMAT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
