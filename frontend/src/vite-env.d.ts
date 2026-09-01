/// <reference types="vite/client" />

// Only client-safe, non-secret variables belong here. Never declare or read
// credentials/passwords from import.meta.env - that bundles them into the
// public JS that ships to every browser.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_API_BASE_LOCAL_URL: string;

  readonly VITE_API_LOGIN_URL: string;
  readonly VITE_SUMMARY_PDF_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
