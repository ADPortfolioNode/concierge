import axios, { AxiosRequestConfig } from 'axios';
import { ACTIVE_API_BASE, API_PREFIX } from '../config/activeServer';
import { reportApiError } from '../utils/errorLogger';

interface AdaptiveAxiosRequestConfig extends AxiosRequestConfig {
  _adaptiveTimer?: ReturnType<typeof setTimeout>;
  _adaptiveCancel?: { cancel: (message?: string) => void };
}

// Timeout is disabled by default (0 = no limit) to accommodate slow LLM
// inference and large file uploads.  Override via the VITE_API_TIMEOUT env
// variable (milliseconds) if you want an explicit cap, e.g. VITE_API_TIMEOUT=120000.
const _envTimeout = import.meta.env.VITE_API_TIMEOUT;
const defaultTimeout = _envTimeout !== undefined ? Number(_envTimeout) : 0;

// Use central ACTIVE_API_BASE (resolved from Vite envs) and append API prefix.
const base = (ACTIVE_API_BASE || '').replace(/\/$/, '');
const apiClient = axios.create({
  baseURL: `${base}${API_PREFIX}`,
  timeout: defaultTimeout, // 0 = no Axios built-in timeout
});

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