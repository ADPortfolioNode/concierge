import apiClient from './client';
import { ApiResponse } from '../types/api';
import { makeApiUrl } from '@/config/activeServer';
import { ConversationMessage } from '../types/domain';

// A single turn in the conversation history sent to the backend.
// Industry-standard hybrid memory: the browser keeps the full thread in
// IndexedDB and forwards it on every call so the backend has full context.
type HistoryEntry = Pick<ConversationMessage, 'role' | 'content'>;

export const sendMessage = async (message: string, history?: HistoryEntry[]) => {
  if (!message || !message.trim()) {
    throw new Error('message must be a nonempty string');
  }
  const res = await apiClient.post<ApiResponse>('/concierge/message', { message, history });
  if ((res as any).error) {
    throw new Error((res as any).error);
  }
  return res;
};

export const fetchConversation = async () => {
  const res = await apiClient.get<ApiResponse>('/concierge/conversation');
  if ((res as any).error) {
    throw new Error((res as any).error);
  }
  return res;
};

export const getTimeline = async () => {
  const res = await apiClient.get<ApiResponse>('/concierge/timeline');
  if ((res as any).error) {
    throw new Error((res as any).error);
  }
  return res;
};

export const getMedia = async () => {
  const res = await apiClient.get<ApiResponse>('/concierge/media');
  if ((res as any).error) throw new Error((res as any).error);
  return res;
};

// ── SSE streaming ──────────────────────────────────────────────────────────
// Event shapes emitted by the backend (see SacredTimeline.stream_user_input):
//   { type: 'token',    text: string }   — single LLM output fragment
//   { type: 'progress', text: string }   — orchestration status update
//   { type: 'done',     result: object } — final structured payload
//   { type: 'error',    text: string }   — terminal error
export type StreamEvent =
  | { type: 'token';    text: string }
  | { type: 'progress'; text: string }
  | { type: 'done';     result: Record<string, unknown> }
  | { type: 'error';    text: string };

/**
 * Opens an SSE connection to POST /api/v1/concierge/stream and yields each
 * parsed event.  The generator closes when it receives `[DONE]` or an error.
 *
 * Uses the native Fetch API + ReadableStream so there is no Axios timeout on
 * the streaming leg (Axios cannot stream SSE natively).
 *
 * Pass the optional `history` array (prior conversation turns) so the backend
 * receives full context on every call (hybrid memory pattern).
 */
export async function* streamMessage(message: string, history?: HistoryEntry[]): AsyncGenerator<StreamEvent> {
  const streamUrl = makeApiUrl('/api/v1/concierge/stream');

  const response = await fetch(streamUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';   // keep the incomplete trailing line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') return;
        try {
          yield JSON.parse(payload) as StreamEvent;
        } catch {
          // malformed event — skip
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {/* ignore */});
  }
}
