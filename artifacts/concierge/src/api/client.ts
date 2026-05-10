import axios from 'axios';
import { API_PREFIX } from '../config/activeServer';
import { reportApiError } from '../utils/errorLogger';

const apiClient = axios.create({
  baseURL: API_PREFIX,
  timeout: 0,
});

apiClient.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  config.headers['X-Request-ID'] = generateRequestId();
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    try {
      reportApiError(error instanceof Error ? error : new Error(String(error)));
    } catch {
      // ignore reporting failures
    }
    return Promise.reject(error);
  }
);

function generateRequestId() {
  const c = typeof crypto !== 'undefined' ? (crypto as unknown as { randomUUID?: () => string }) : undefined;
  if (c?.randomUUID) return c.randomUUID();
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function apiRequest(
  input: string,
  init?: { method?: string; headers?: Record<string, string>; body?: unknown }
) {
  try {
    const response = await apiClient.request({
      url: input,
      method: init?.method || 'GET',
      headers: init?.headers,
      data: init?.body,
    });
    return response.data;
  } catch (err: unknown) {
    let message = 'Unknown error';
    if (axios.isAxiosError(err)) {
      if (err.response) message = `API error: ${err.response.status}`;
      else if (err.request) message = 'Network error: no response received';
      else if (err.message) message = err.message;
    } else if (err instanceof Error) {
      message = err.message;
    }
    return { error: message };
  }
}

export default apiClient;
