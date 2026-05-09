// centralized error logging/handling for the frontend

export type ApiErrorHandler = (err: Error) => void;

let currentHandler: ApiErrorHandler | null = null;

/**
 * Register a callback that will be invoked whenever an API error is detected.
 * Multiple registrations overwrite the previous handler; if you need a list,
 * wrap accordingly.
 */
export function setApiErrorHandler(handler: ApiErrorHandler) {
  currentHandler = handler;
}

/**
 * Internal helper used by the API clients to notify about errors. Always
 * logs to console so that issues are visible during development.
 */
export function reportApiError(err: Error) {
  // never swallow the error; mirror it in dev console
  console.error('[API ERROR]', err);
  if (currentHandler) {
    try {
      currentHandler(err);
    } catch (e) {
      // if the handler itself throws, log but don't crash the app
      console.error('apiErrorHandler threw', e);
    }
  }
}
