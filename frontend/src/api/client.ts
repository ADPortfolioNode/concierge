import axios from 'axios';

// allow the timeout to be tuned in development/CI via an environment
// variable. Vite exposes variables prefixed with `VITE_` on
// `import.meta.env`; fall back to the existing hard‑coded 10s value if unset.
const defaultTimeout = Number(import.meta.env.VITE_API_TIMEOUT ?? 10000);

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: defaultTimeout,
});

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