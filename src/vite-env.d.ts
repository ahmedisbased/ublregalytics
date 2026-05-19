/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_APP_USERNAME: string;
  readonly VITE_APP_PASSWORD: string;
  readonly VITE_SUMMARY_PDF_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
