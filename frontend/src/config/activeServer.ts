// Centralize selection of the active API server for dev, Docker, staging, and production.
const env = (import.meta as any).env || {};

const MODE = env.MODE || (env.DEV ? 'development' : env.PROD ? 'production' : 'production');
const VITE_API_URL = (env.VITE_API_URL || env.BACKEND_URL || '').replace(/\/$/, '');
const VITE_API_URL_LOCAL = (env.VITE_API_URL_LOCAL || '').replace(/\/$/, '');
const VITE_API_URL_DOCKER = (env.VITE_API_URL_DOCKER || '').replace(/\/$/, '');
const VITE_API_URL_STAGING = (env.VITE_API_URL_STAGING || '').replace(/\/$/, '');
const VITE_API_URL_PRODUCTION = (env.VITE_API_URL_PRODUCTION || '').replace(/\/$/, '');
const VITE_API_URL_SET = (env.VITE_API_URL_SET || env.VITE_API_SERVER_SET || '').trim().toLowerCase();
const VITE_API_URL_AUTO_DETECT = (env.VITE_API_URL_AUTO_DETECT || 'true').toLowerCase() !== 'false';

// Support a runtime-self placeholder: if the build-time env is set to
// "<self.server>" we'll treat it as an instruction to use the page
// origin at runtime (same-origin deployments). Normalize to an empty
// string so the runtime fallback in `makeApiUrl` will use
// `window.location.origin`.
const normalizeServerUrl = (url: string) => url.replace(/\/$/, '');

const parseHostname = (url: string) => {
  try {
    const parsed = new URL(url);
    return parsed.hostname.toLowerCase();
  } catch {
    return '';
  }
};

const PRODUCTION_HOST = parseHostname(VITE_API_URL_PRODUCTION);
const STAGING_HOST = parseHostname(VITE_API_URL_STAGING);

const detectServerSet = (): string => {
  if (typeof window === 'undefined' || !window.location) {
    return MODE === 'development' ? 'local' : 'production';
  }

  const host = window.location.hostname.toLowerCase();

  if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
    return 'local';
  }

  if (host === 'app' || host === 'backend' || host.endsWith('.internal')) {
    return 'docker';
  }

  if (STAGING_HOST && host === STAGING_HOST) {
    return 'staging';
  }

  if (PRODUCTION_HOST && host === PRODUCTION_HOST) {
    return 'production';
  }

  if (host.includes('ngrok') || host.endsWith('.ngrok-free.app') || host.endsWith('.ngrok-free.dev') || host.endsWith('.ngrok.io')) {
    return 'staging';
  }

  if (host.endsWith('.vercel.app') || host.endsWith('.vercel.sh') || host.endsWith('.now.sh')) {
    return 'production';
  }

  return 'production';
};

const ACTIVE_SERVER = (() => {
  const isLocalHost = typeof window !== 'undefined' && window.location && ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname.toLowerCase());
  if (isLocalHost) {
    return 'local';
  }
  if (VITE_API_URL_SET) {
    return VITE_API_URL_SET;
  }
  if (VITE_API_URL && VITE_API_URL !== '<self.server>') {
    return 'auto';
  }
  if (!VITE_API_URL_AUTO_DETECT) {
    return MODE === 'development' ? 'local' : 'production';
  }
  return detectServerSet();
})();

export const ACTIVE_SERVER_SET = ACTIVE_SERVER;

const SERVER_URLS: Record<string, string> = {
  local: normalizeServerUrl(VITE_API_URL_LOCAL || VITE_API_URL || 'http://localhost:8001'),
  docker: normalizeServerUrl(VITE_API_URL_DOCKER || VITE_API_URL || 'http://app:8000'),
  staging: normalizeServerUrl(VITE_API_URL_STAGING || VITE_API_URL || ''),
  production: normalizeServerUrl(VITE_API_URL_PRODUCTION || VITE_API_URL || ''),
  auto: normalizeServerUrl(VITE_API_URL || ''),
};

export const ACTIVE_API_BASE: string = (() => {
  const candidate = SERVER_URLS[ACTIVE_SERVER_SET] ?? SERVER_URLS.local;
  if (MODE === 'production') {
    return candidate === '<self.server>' ? '' : candidate;
  }
  return candidate || 'http://localhost:8001';
})();

// Build a full URL for API paths. If the active base is empty, return a relative path.
export function makeApiUrl(path: string) {
  if (!path) return path;
  const p = path.startsWith('/') ? path : `/${path}`;
  if (!ACTIVE_API_BASE) {
    // If no build-time API base was provided, prefer the current page origin
    // when running in a browser so the app automatically targets the
    // server that served the frontend (works for same-origin deploys).
    if (typeof window !== 'undefined' && window.location && window.location.origin) {
      return `${window.location.origin}${p}`;
    }
    return p;
  }
  return `${ACTIVE_API_BASE}${p}`;
}

export const ACTIVE_API_BASE_URL = ACTIVE_API_BASE;

export default { ACTIVE_API_BASE, ACTIVE_API_BASE_URL, ACTIVE_SERVER_SET, makeApiUrl };
