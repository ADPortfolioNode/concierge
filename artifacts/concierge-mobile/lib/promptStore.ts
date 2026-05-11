/**
 * Lightweight module-level store for passing a pending prompt
 * from Goals / Strategy / Workspace screens to the Chat tab.
 * Using a simple pub/sub so the Chat screen can react when it focuses.
 */

type Listener = (prompt: string) => void;

let _pending: string | null = null;
const _listeners: Set<Listener> = new Set();

export function setPendingPrompt(text: string) {
  _pending = text;
  _listeners.forEach((fn) => fn(text));
}

export function consumePendingPrompt(): string | null {
  const p = _pending;
  _pending = null;
  return p;
}

export function onPendingPrompt(fn: Listener): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}
