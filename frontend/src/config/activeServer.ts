// Centralize selection of the active API server for dev vs production.
const env = (import.meta as any).env || {};

const MODE = env.MODE || (env.DEV ? 'development' : env.PROD ? 'production' : 'production');
const VITE_API_URL = (env.VITE_API_URL || '').replace(/\/$/, '');
const VITE_LOCAL_API_URL = (env.VITE_LOCAL_API_URL || '').replace(/\/$/, '');

// ACTIVE_API_BASE resolution rules:
// - In development: prefer VITE_LOCAL_API_URL, then VITE_API_URL, then localhost fallback.
// - In production: require VITE_API_URL (throws early if missing) to avoid bundling a localhost.
export const ACTIVE_API_BASE: string = (() => {
  if (MODE === 'development') {
    return VITE_LOCAL_API_URL || VITE_API_URL || 'http://localhost:8001';
  }
  if (!VITE_API_URL) {
    throw new Error(
      'VITE_API_URL must be set in production builds. Set VITE_API_URL to your backend base URL (e.g. https://api.example.com)'
    );
  }
  return VITE_API_URL;
})();

// Build a full URL for API paths. If the active base is empty, return a relative path.
export function makeApiUrl(path: string) {
  if (!path) return path;
  const p = path.startsWith('/') ? path : `/${path}`;
  if (!ACTIVE_API_BASE) return p;
  return `${ACTIVE_API_BASE}${p}`;
}

export default { ACTIVE_API_BASE, makeApiUrl };
