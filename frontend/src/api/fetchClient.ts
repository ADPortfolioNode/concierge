// lightweight wrapper around window.fetch to enforce strict API contract

import { reportApiError } from '../utils/errorLogger';

export async function handleResponse(response: Response) {
  // non-2xx status codes
  if (!response.ok) {
    const text = await response.text();
    const err = new Error(
      `API Error ${response.status}: ${text || 'No response body'}`
    );
    reportApiError(err);
    throw err;
  }

  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    const text = await response.text();
    const err = new Error(
      `Invalid content-type: ${contentType}. Body: ${text}`
    );
    reportApiError(err);
    throw err;
  }

  // At this point we expect valid JSON, let the caller parse it
  return response.json();
}

export async function apiRequest(
  input: RequestInfo,
  init?: RequestInit
): Promise<any> {
  const response = await fetch(input, init);
  return handleResponse(response);
}
