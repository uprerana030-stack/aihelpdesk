// Central runtime config. In development, use a relative base URL so Vite can
// proxy requests to the FastAPI backend. In production, honor the configured
// API URL or fall back to localhost for local testing.
const env = (typeof import.meta !== 'undefined' && import.meta.env) || {};

export function resolveApiBaseUrl(runtimeEnv = env) {
  const configuredUrl = runtimeEnv.VITE_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl;
  }

  if (runtimeEnv.MODE === 'development') {
    return '';
  }

  return 'http://localhost:8000';
}

// Backend is served over plain HTTP (no TLS), so there is no SSL certificate
// for the browser to verify. In dev, the Vite dev server proxies requests to
// the FastAPI backend so the browser can reach it without CORS issues.
export const API_BASE_URL = resolveApiBaseUrl(env);

export const SESSION_STORAGE_KEY = 'helpdesk_user';
