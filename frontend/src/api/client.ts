import axios from 'axios';

// Timeout is disabled by default (0 = no limit) to accommodate slow LLM
// inference and large file uploads.  Override via the VITE_API_TIMEOUT env
// variable (milliseconds) if you want an explicit cap, e.g. VITE_API_TIMEOUT=120000.
const _envTimeout = import.meta.env.VITE_API_TIMEOUT;
const defaultTimeout = _envTimeout !== undefined ? Number(_envTimeout) : 0;

// allow overriding the backend host via environment variable (Vite runtime).
// when running the dev frontend server on :5173 we need to call the real
// API on :8001, otherwise requests will go to the same origin and fail with
// 503/404. VITE_API_URL should include protocol and port but no trailing slash.
const _viteApiUrl = (import.meta as any).env?.VITE_API_URL;
// In production builds we require an explicit backend URL to avoid bundling
// a localhost default into a deployed asset. This helps prevent remote
// users of the deployed frontend from attempting to contact `localhost:8001`.
if ((import.meta as any).env && (import.meta as any).env.PROD && !_viteApiUrl) {
  throw new Error(
    'VITE_API_URL must be set in production builds. Set VITE_API_URL to your backend base URL (e.g. https://api.example.com)'
  );
}
const base = ((_viteApiUrl) || 'http://localhost:8001').replace(/\/$/, '');
const apiClient = axios.create({
  baseURL: `${base}/api/v1`,
  timeout: defaultTimeout,   // 0 = no Axios built-in timeout
});

// Helper to start/stop adaptive timeout timers. We attach the timer and
// cancel source to the request config so they can be cleaned up by the
// response interceptor later.  If a progress event is fired the timer is
// restarted, which effectively grants another `timeout` ms of grace.  This
// avoids failures when a slow-but-steady response is arriving in chunks.
function attachAdaptiveTimeout(config: any) {
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
  config.onDownloadProgress = (evt: any) => {
    start();
    if (typeof origDownload === 'function') origDownload(evt);
  };
  const origUpload = config.onUploadProgress;
  config.onUploadProgress = (evt: any) => {
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
    if ((response.config as any)._adaptiveTimer) {
      clearTimeout((response.config as any)._adaptiveTimer);
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
  (error) => {
    // clear timer on error as well
    if (error.config && (error.config as any)._adaptiveTimer) {
      clearTimeout((error.config as any)._adaptiveTimer);
    }

    // notify logging system
    try {
      // lazy-import to avoid circular deps
      const { reportApiError } = require('../utils/errorLogger');
      reportApiError(error instanceof Error ? error : new Error(String(error)));
    } catch {}
    // normalize error
    if (error.response) {
      // handle 401, 500 globally
      if (error.response.status === 401) {
        // redirect to login or similar
      }
    }
    return Promise.reject(error);
  }
);


// request interceptor
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
  return config;
});

// response interceptor (success path validates contract, error path normalizes)
apiClient.interceptors.response.use(
  (response) => {
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
  (error) => {
    // notify logging system
    try {
      // lazy-import to avoid circular deps
      const { reportApiError } = require('../utils/errorLogger');
      reportApiError(error instanceof Error ? error : new Error(String(error)));
    } catch {}
    // normalize error
    if (error.response) {
      // handle 401, 500 globally
      if (error.response.status === 401) {
        // redirect to login or similar
      }
    }
    return Promise.reject(error);
  }
);

function generateRequestId() {
  return crypto.randomUUID();
}

// convenience helper that mirrors fetch-style API but still uses axios
// and provides a defensive wrapper. callers may expect an object with a
// `status` or check for `error` rather than blindly mutating state.
export async function apiRequest(
  input: string,
  init?: {
    method?: string;
    headers?: Record<string, string>;
    body?: any;
  }
) {
  const config: any = {
    url: input,
    method: init?.method || 'GET',
    headers: init?.headers,
    data: init?.body,
  };

  try {
    const response = await apiClient.request(config);
    // axios already parses JSON; if we reach here response.data is usable
    return response.data;
  } catch (err: any) {
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
    return { error: message } as any;
  }
}

export default apiClient;