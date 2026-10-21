/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CHAIN?: string;
  readonly VITE_PREDICTION_MARKET_ADDRESS?: string;
  readonly VITE_ACON_TOKEN_ADDRESS?: string;
  readonly VITE_DEMO_MARKET_ID?: string;
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
