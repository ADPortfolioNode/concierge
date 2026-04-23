import axios, { AxiosRequestConfig } from 'axios';
import { ACTIVE_API_BASE, API_PREFIX } from '../config/activeServer';
import { reportApiError } from '../utils/errorLogger';

interface AdaptiveAxiosRequestConfig extends AxiosRequestConfig {
  _adaptiveTimer?: ReturnType<typeof setTimeout>;
  _adaptiveCancel?: { cancel: (message?: string) => void };
  _retryWithLocalFallback?: boolean;
  _localFallbackAttempts?: string[];
  _localFallbackIndex?: number;
}

// Timeout is disabled by default (0 = no limit) to accommodate slow LLM
// inference and large file uploads.  Override via the VITE_API_TIMEOUT env
// variable (milliseconds) if you want an explicit cap, e.g. VITE_API_TIMEOUT=120000.
const _envTimeout = import.meta.env.VITE_API_TIMEOUT;
const defaultTimeout = _envTimeout !== undefined ? Number(_envTimeout) : 0;

// Use central ACTIVE_API_BASE (resolved from Vite envs) and append API prefix.
const VITE_BACKEND_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || import.meta.env.BACKEND_URL || '';
const VITE_API_URL_LOCAL = import.meta.env.VITE_API_URL_LOCAL || '';
const localFallbackBase = VITE_BACKEND_URL || VITE_API_URL_LOCAL || 'http://127.0.0.1:8001';
const base = ((ACTIVE_API_BASE || (import.meta.env.DEV ? localFallbackBase : ''))).replace(/\/$/, '');
const apiClient = axios.create({
  baseURL: `${base}${API_PREFIX}`,
  timeout: defaultTimeout, // 0 = no Axios built-in timeout
});

function shouldRetryLocalPortFallback(error: unknown): error is axios.AxiosError {
  return axios.isAxiosError(error) && !!error.config && !error.response && !!error.request;
}

function buildLocalFallbackBases(baseURL: string): string[] {
  const fallbacks: string[] = [];
  const primary = baseURL.trim();
  const hasPort8001 = primary.includes(':8001');
  const hasPort8000 = primary.includes(':8000');
  const hasLocalHost = primary.includes('localhost');
  const has127Local = primary.includes('127.0.0.1');

  if (primary && (hasPort8001 || hasPort8000)) {
    if (hasPort8001) {
      fallbacks.push(primary.replace(':8001', ':8000'));
      if (!hasLocalHost) fallbacks.push(primary.replace('127.0.0.1:8001', 'localhost:8001'));
      if (!has127Local) fallbacks.push(primary.replace('localhost:8001', '127.0.0.1:8001'));
    }
    if (hasPort8000) {
      fallbacks.push(primary.replace(':8000', ':8001'));
      if (!hasLocalHost) fallbacks.push(primary.replace('127.0.0.1:8000', 'localhost:8000'));
      if (!has127Local) fallbacks.push(primary.replace('localhost:8000', '127.0.0.1:8000'));
    }
  } else if (!primary && import.meta.env.DEV) {
    fallbacks.push('http://127.0.0.1:8001');
    fallbacks.push('http://localhost:8001');
    fallbacks.push('http://127.0.0.1:8000');
    fallbacks.push('http://localhost:8000');
  }

  return Array.from(new Set(fallbacks)).filter((url) => !!url);
}

function retryLocalPortFallback(config: AdaptiveAxiosRequestConfig) {
  if (config._adaptiveCancel?.cancel) {
    config._adaptiveCancel.cancel('retrying with alternate local port');
  }

  const baseURL = config.baseURL || '';
  const candidates = config._localFallbackAttempts || buildLocalFallbackBases(baseURL);
  const nextIndex = typeof config._localFallbackIndex === 'number' ? config._localFallbackIndex + 1 : 0;
  if (nextIndex >= candidates.length) {
    return null;
  }

  const fallbackConfig: AdaptiveAxiosRequestConfig = {
    ...config,
    baseURL: candidates[nextIndex],
    _retryWithLocalFallback: true,
    _localFallbackAttempts: candidates,
    _localFallbackIndex: nextIndex,
  };

  return apiClient.request(fallbackConfig);
}

// Helper to start/stop adaptive timeout timers. We attach the timer and
// cancel source to the request config so they can be cleaned up by the
// response interceptor later.  If a progress event is fired the timer is
// restarted, which effectively grants another `timeout` ms of grace.  This
// avoids failures when a slow-but-steady response is arriving in chunks.
function attachAdaptiveTimeout(config: AdaptiveAxiosRequestConfig) {
  // Treat 0 / undefined as "disabled" — do not install a cancel timer.
  const timeout = (config.timeout != null ? config.timeout : defaultTimeout);
  if (!timeout) return;  // 0 means no timeout
  const source = axios.CancelToken.source();
  config.cancelToken = source.token;

  let timer: ReturnType<typeof setTimeout> | null = null;
  const start = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      source.cancel(`timeout of ${timeout}ms exceeded`);
    }, timeout);
  };

  // wire up progress callbacks
  const origDownload = config.onDownloadProgress;
  config.onDownloadProgress = (evt: ProgressEvent) => {
    start();
    if (typeof origDownload === 'function') origDownload(evt);
  };
  const origUpload = config.onUploadProgress;
  config.onUploadProgress = (evt: ProgressEvent) => {
    start();
    if (typeof origUpload === 'function') origUpload(evt);
  };

  // store for cleanup later
  config._adaptiveTimer = timer;
  config._adaptiveCancel = source;

  // kick off initial timer
  start();
}

// request interceptor: add request id and adaptive timeout logic
apiClient.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  // attach request id or other logging info
  config.headers['X-Request-ID'] = generateRequestId();
  // auto-authorize in development when enabled
  try {
    const auto = (typeof window !== 'undefined' && window.localStorage && window.localStorage.getItem('AUTO_AUTHORIZE')) || null;
    if (auto === 'yes') {
      config.headers['Authorization'] = 'Bearer dev-auto-token';
    }
  } catch (e) {
    // ignore
  }

  // set up adaptive timeout before the request is sent
  attachAdaptiveTimeout(config);

  return config;
});

// response interceptor (success path validates contract, error path normalizes)
apiClient.interceptors.response.use(
  (response) => {
    // clear any timeout timer that was running
    const responseConfig = response.config as AdaptiveAxiosRequestConfig;
    if (responseConfig._adaptiveTimer) {
      clearTimeout(responseConfig._adaptiveTimer);
    }

    // axios treats non-2xx as errors and skips this handler, so we only
    // need to check for malformed 2xx responses here.
    const contentType: string = response.headers['content-type'] || '';
    if (!contentType.includes('application/json')) {
      // axios already read the body into response.data; convert to string
      const bodyText =
        typeof response.data === 'string'
          ? response.data
          : JSON.stringify(response.data);
      return Promise.reject(
        new Error(`Invalid content-type: ${contentType}. Body: ${bodyText}`)
      );
    }

    // ensure we actually got something parsable
    if (response.data == null) {
      return Promise.reject(
        new Error(
          `Empty response body for ${response.config.method?.toUpperCase()} ${response.config.url}`
        )
      );
    }

    return response;
  },
  (error: unknown) => {
    const err = axios.isAxiosError(error) ? error : undefined;
    const cfg = err?.config as AdaptiveAxiosRequestConfig | undefined;
    if (cfg?._adaptiveTimer) {
      clearTimeout(cfg._adaptiveTimer);
    }

    try {
      reportApiError(err instanceof Error ? err : new Error(String(error)));
    } catch (reportError) {
      // ignore reporting failures
    }

    if (err?.response) {
      if (err.response.status === 401) {
        // redirect to login or similar
      }
      return Promise.reject(error);
    }

    if (shouldRetryLocalPortFallback(error) && typeof error.config.baseURL === 'string') {
      const backupCandidates = (error.config as AdaptiveAxiosRequestConfig)._localFallbackAttempts;
      const currentIndex = (error.config as AdaptiveAxiosRequestConfig)._localFallbackIndex ?? -1;
      const hasMoreFallbacks = Array.isArray(backupCandidates) && currentIndex + 1 < backupCandidates.length;
      if (
        (error.config.baseURL.includes(':8001') || error.config.baseURL.includes(':8000') || error.config.baseURL === '') ||
        hasMoreFallbacks
      ) {
        return retryLocalPortFallback(error.config as AdaptiveAxiosRequestConfig) || Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

function generateRequestId() {
  const cryptoObj = typeof crypto !== 'undefined' ? (crypto as unknown as { randomUUID?: () => string }) : undefined;
  if (cryptoObj?.randomUUID) {
    return cryptoObj.randomUUID();
  }
  // fallback for environments without crypto.randomUUID
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

// convenience helper that mirrors fetch-style API but still uses axios
// and provides a defensive wrapper. callers may expect an object with a
// `status` or check for `error` rather than blindly mutating state.
export async function apiRequest(
  input: string,
  init?: {
    method?: string;
    headers?: Record<string, string>;
    body?: unknown;
  }
) {
  const config: AxiosRequestConfig = {
    url: input,
    method: init?.method || 'GET',
    headers: init?.headers,
    data: init?.body,
  };

  try {
    const response = await apiClient.request(config);
    // axios already parses JSON; if we reach here response.data is usable
    return response.data;
  } catch (err: unknown) {
    // normalize to an Error instance with user-friendly message
    let message = 'Unknown error';
    if (axios.isAxiosError(err)) {
      if (err.response) {
        message = `API error: ${err.response.status}`;
      } else if (err.request) {
        message = 'Network error: no response received';
      } else if (err.message) {
        message = err.message;
      }
    } else if (err instanceof Error) {
      message = err.message;
    }
    // we return a structured object instead of throwing to avoid unhandled
    // promise rejections in components; callers can still throw if desired.
    return { error: message };
  }
}

export default apiClient;