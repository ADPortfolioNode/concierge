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
  streamingId: string | null;   // id of the in-flight assistant bubble
  draftMessage: string;         // prefill value for the chat input
  error: string | null;
  setError: (msg: string | null) => void;
  setDraft: (text: string) => void;
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
  streamingId: null,
  draftMessage: '',
  error: null,
  setError: (msg) => set({ error: msg }),
  setDraft: (text) => set({ draftMessage: text }),
  setConversation: (msgs) => set({ conversation: msgs }),
  setActiveMedia: (url) => set({ activeMedia: url }),
  appendMessage: (msg) => set((s) => ({ conversation: [...s.conversation, msg] })),

  sendMessage: async (input: string) => {
    const userMsgId = String(Date.now());
    const assistantMsgId = String(Date.now() + 1);

    // Optimistic: show user message immediately
    const userMsg: ConversationMessage = {
      id: userMsgId,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
      media: null,
      meta: null,
    };
    // Placeholder assistant bubble that will be updated token-by-token
    const placeholderMsg: ConversationMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      media: null,
      meta: null,
    };

    set((s) => ({
      conversation: [...s.conversation, userMsg, placeholderMsg],
      loading: true,
      streamingId: assistantMsgId,
      error: null,
    }));

    try {
      let accumulated = '';

      for await (const evt of ConciergeAPI.streamMessage(input)) {
        if (evt.type === 'token' || evt.type === 'progress') {
          accumulated += evt.text;
          // Patch the placeholder bubble with the accumulated text
          set((s) => ({
            conversation: s.conversation.map((m) =>
              m.id === assistantMsgId ? { ...m, content: accumulated } : m,
            ),
          }));
        } else if (evt.type === 'done') {
          // Finalise: if result has a cleaner summary use it
          const result = evt.result as Record<string, unknown>;
          const finalText: string =
            (result?.final as any)?.summary ||
            (result?.response as string) ||
            accumulated;
          const metaResult = result as Record<string, any>;
          const confidence = metaResult?.final?.confidence ?? metaResult?.confidence ?? undefined;
          const critic_score = metaResult?.final?.critic_score ?? metaResult?.critic_score ?? undefined;
          set((s) => ({
            conversation: s.conversation.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: finalText || accumulated, meta: {
                    confidence: typeof confidence === 'number' ? confidence : undefined,
                    critic_score: typeof critic_score === 'number' ? critic_score : undefined,
                  } }
                : m,
            ),
          }));
        } else if (evt.type === 'error') {
          set((s) => ({
            conversation: s.conversation.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: `⚠️ ${evt.text}` }
                : m,
            ),
            error: evt.text,
          }));
        }
      }
    } catch (e) {
      const errText = e instanceof Error ? e.message : String(e);
      // Replace the placeholder with the error
      set((s) => ({
        conversation: s.conversation.map((m) =>
          m.id === assistantMsgId ? { ...m, content: `⚠️ ${errText}` } : m,
        ),
        error: errText,
      }));
    } finally {
      set({ loading: false, streamingId: null });
    }
  },
}));
