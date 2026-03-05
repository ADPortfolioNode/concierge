import { create } from 'zustand';
import { ConversationMessage } from '../types/domain';
import * as ConciergeAPI from '@/api/conciergeService';

interface AppState {
  conversation: ConversationMessage[];
  activeMedia: string | null;
  currentTaskId: string | null;
  currentGoalId: string | null;
  confidence: number;
  priority: number;
  loading: boolean;
  error: string | null;
  setError: (msg: string | null) => void;
  setConversation: (msgs: ConversationMessage[]) => void;
  setActiveMedia: (url: string | null) => void;
  appendMessage: (msg: ConversationMessage) => void;
  sendMessage: (input: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  conversation: [],
  activeMedia: null,
  currentTaskId: null,
  currentGoalId: null,
  confidence: 0,
  priority: 0,
  loading: false,
  error: null,
  setError: (msg) => set({ error: msg }),
  setConversation: (msgs) => set({ conversation: msgs }),
  setActiveMedia: (url) => set({ activeMedia: url }),
  appendMessage: (msg) => set((s) => ({ conversation: [...s.conversation, msg] })),
  sendMessage: async (input: string) => {
    set({ loading: true, error: null });
    try {
      const resp = await ConciergeAPI.sendMessage(input);
      // expect the backend to return a message envelope or conversation
      const payload = resp?.data?.data;
      if (!payload) {
        throw new Error('Invalid response');
      }

      // Normalize payload: backend may return structured objects in
      // `content` (or JSON-stringified objects). Attempt to parse JSON
      // strings so the UI can render structured fields like `summary`.
      let parsedPayload: any = payload;
      try {
        if (payload && typeof payload === 'object') {
          const c = payload.content;
          if (typeof c === 'string') {
            const t = c.trim();
            if (t.startsWith('{') || t.startsWith('[')) {
              try {
                parsedPayload = { ...payload, content: JSON.parse(c) };
              } catch (e) {
                // leave as-is if parse fails
              }
            }
          }
        } else if (typeof payload === 'string') {
          const t = payload.trim();
          if (t.startsWith('{') || t.startsWith('[')) {
            try {
              parsedPayload = JSON.parse(payload);
            } catch (e) {
              // ignore
            }
          }
        }
      } catch (e) {
        // best-effort; continue with original payload
        parsedPayload = payload;
      }

      if (Array.isArray(parsedPayload)) {
        // replace or append conversation array as provided
        set({ conversation: parsedPayload });
        // pick latest media if provided in meta
        const last = parsedPayload[parsedPayload.length - 1];
        if (last?.media?.url) set({ activeMedia: last.media.url });
      } else {
        // payload is a single message
        // prefer structured content.summary when available
        let contentText = '';
        const cont = parsedPayload.content ?? parsedPayload.text ?? '';
        if (typeof cont === 'string') {
          contentText = cont;
        } else if (cont && typeof cont === 'object') {
          if (cont.summary) contentText = cont.summary;
          else contentText = JSON.stringify(cont);
        } else {
          contentText = String(cont || '');
        }

        const msg: ConversationMessage = {
          id: parsedPayload.id || String(Date.now()),
          role: parsedPayload.role || 'assistant',
          content: contentText,
          timestamp: parsedPayload.timestamp || new Date().toISOString(),
          media: parsedPayload.media || null,
          meta: parsedPayload.meta || null,
        };
        set((s) => ({ conversation: [...s.conversation, msg] }));
        if (parsedPayload?.media?.url) set({ activeMedia: parsedPayload.media.url });
      }
    } catch (e) {
      // report to central logger so that the app can hook in analytics or
      // display global error notifications
      try {
        const { reportApiError } = require('../utils/errorLogger');
        if (e instanceof Error) reportApiError(e);
        else reportApiError(new Error(String(e)));
      } catch {}

      // set error state; UI will render a banner.
      set({ error: String(e) });
    } finally {
      set({ loading: false });
    }
  },
}));
