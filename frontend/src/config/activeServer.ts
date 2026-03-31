// Centralize selection of the active API server for dev vs production.
const env = (import.meta as any).env || {};

const MODE = env.MODE || (env.DEV ? 'development' : env.PROD ? 'production' : 'production');
const VITE_API_URL = (env.VITE_API_URL || '').replace(/\/$/, '');
const VITE_LOCAL_API_URL = (env.VITE_LOCAL_API_URL || '').replace(/\/$/, '');

// Support a runtime-self placeholder: if the build-time env is set to
// "<self.server>" we'll treat it as an instruction to use the page
// origin at runtime (same-origin deployments). Normalize to an empty
// string so the runtime fallback in `makeApiUrl` will use
// `window.location.origin`.
// Treat the placeholder from this repo's samples as unset.
const isPlaceholder = (url: string) => !url || url === '<self.server>' || url.startsWith('https://api.example');
const NORMALIZED_VITE_API_URL = isPlaceholder(VITE_API_URL) ? '' : VITE_API_URL;
const NORMALIZED_VITE_LOCAL_API_URL = isPlaceholder(VITE_LOCAL_API_URL) ? '' : VITE_LOCAL_API_URL;

// ACTIVE_API_BASE resolution rules:
// - In development: prefer VITE_LOCAL_API_URL, then VITE_API_URL, then localhost fallback.
// - In production: prefer VITE_API_URL or runtime origin fallback in `makeApiUrl`.
export const ACTIVE_API_BASE: string = (() => {
  if (MODE === 'development') {
    return NORMALIZED_VITE_LOCAL_API_URL || NORMALIZED_VITE_API_URL || 'http://localhost:8001';
  }
  // In production prefer an explicit VITE_API_URL, but do not throw: when
  // it's not provided (or is the <self.server> placeholder), return an
  // empty string so `makeApiUrl` will fall back at runtime to the page
  // origin (same-origin deploys). This avoids baking hostnames into
  // built assets and supports runtime server detection.
  return NORMALIZED_VITE_API_URL || '';
})();

// Build a full URL for API paths. If the active base is empty, return a relative path.
export function makeApiUrl(path: string) {
  if (!path) return path;
  const p = path.startsWith('/') ? path : `/${path}`;
  if (!ACTIVE_API_BASE) {
    if (typeof window !== 'undefined' && window.location && window.location.origin) {
      return `${window.location.origin}${p}`;
    }
    return p;
  }
  return `${ACTIVE_API_BASE}${p}`;
}

// Asset base URL (logo, stylesheets, static media)
const VITE_ASSET_BASE = (env.VITE_ASSET_BASE || '').replace(/\/$/, '');
const NORMALIZED_VITE_ASSET_BASE = isPlaceholder(VITE_ASSET_BASE) ? '' : VITE_ASSET_BASE;
export const ACTIVE_ASSET_BASE: string = NORMALIZED_VITE_ASSET_BASE || '';

export function makeAssetUrl(path: string) {
  if (!path) return path;
  const p = path.startsWith('/') ? path : `/${path}`;
  if (!ACTIVE_ASSET_BASE) {
    if (typeof window !== 'undefined' && window.location && window.location.origin) {
      return `${window.location.origin}${p}`;
    }
    return p;
  }
  return `${ACTIVE_ASSET_BASE}${p}`;
}

export default { ACTIVE_API_BASE, ACTIVE_ASSET_BASE, makeApiUrl, makeAssetUrl };
