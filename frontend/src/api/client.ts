import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
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
  const response = await apiClient.request(config);
  return response.data;
}

export default apiClient;