import { create } from 'zustand';
import { ConversationMessage } from '../types/domain';
import * as ConciergeAPI from '@/api/conciergeService';

export interface MediaItem {
  id: string;
  url: string;
  timestamp: string;
}

// Regexes shared with MediaStage for routing responses to the right layer
const _IMG_RE = /https?:\/\/\S+?\.(?:png|jpg|jpeg|gif|webp|svg|avif)(?:\?\S*)?|https?:\/\/(?:picsum\.photos|i\.imgur\.com|images\.unsplash\.com)\S*/gi;
const _VID_RE = /https?:\/\/\S+?\.(?:mp4|webm)(?:[?#]\S*)?/gi;
const _AUD_RE = /https?:\/\/\S+?\.(?:mp3|wav|m4a)(?:[?#]\S*)?/gi;

interface AppState {
  conversation: ConversationMessage[];
  activeMedia: string | null;
  currentTaskId: string | null;
  currentGoalId: string | null;
  confidence: number;
  priority: number;
  loading: boolean;
  streamingId: string | null;
  draftMessage: string;
  error: string | null;
  // ── media layer state ──────────────────────────────────────────────────
  imageLayers: MediaItem[];
  videoLayers: MediaItem[];
  audioLayers: MediaItem[];
  textHighlights: string[];
  // ── actions ────────────────────────────────────────────────────────────
  setError: (msg: string | null) => void;
  setDraft: (text: string) => void;
  setConversation: (msgs: ConversationMessage[]) => void;
  setActiveMedia: (url: string | null) => void;
  appendMessage: (msg: ConversationMessage) => void;
  pushImage: (url: string) => void;
  pushVideo: (url: string) => void;
  pushAudio: (url: string) => void;
  pushTextHighlight: (text: string) => void;
  clearMediaLayers: () => void;
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
  imageLayers: [],
  videoLayers: [],
  audioLayers: [],
  textHighlights: [],
  setError: (msg) => set({ error: msg }),
  setDraft: (text) => set({ draftMessage: text }),
  setConversation: (msgs) => set({ conversation: msgs }),
  setActiveMedia: (url) => set({ activeMedia: url }),
  appendMessage: (msg) => set((s) => ({ conversation: [...s.conversation, msg] })),
  pushImage: (url) => set((s) => ({
    imageLayers: [...s.imageLayers, { id: `img-${Date.now()}`, url, timestamp: new Date().toISOString() }],
    activeMedia: url,
  })),
  pushVideo: (url) => set((s) => ({
    videoLayers: [...s.videoLayers, { id: `vid-${Date.now()}`, url, timestamp: new Date().toISOString() }],
  })),
  pushAudio: (url) => set((s) => ({
    audioLayers: [...s.audioLayers, { id: `aud-${Date.now()}`, url, timestamp: new Date().toISOString() }],
  })),
  pushTextHighlight: (text) => set((s) => ({
    textHighlights: [...s.textHighlights.slice(-9), text],
  })),
  clearMediaLayers: () => set({ imageLayers: [], videoLayers: [], audioLayers: [], textHighlights: [], activeMedia: null }),

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
          // Finalise: extract a clean human-readable string from the result
          const result = evt.result as Record<string, unknown>;
          const metaResult = result as Record<string, any>;
          const confidence = metaResult?.final?.confidence ?? metaResult?.confidence ?? undefined;
          const critic_score = metaResult?.final?.critic_score ?? metaResult?.critic_score ?? undefined;
          const resp = result?.response;
          const finalText: string = (() => {
            // 1. Non-empty summary from orchestration final pass
            const s = (result?.final as any)?.summary || (result?.summary as string);
            if (typeof s === 'string' && s.trim()) return s.trim();
            // 2. response field — only if it reads like plain prose, not a raw error/object dump
            if (typeof resp === 'string' && resp.trim()) {
              if (resp.startsWith('[LLM-Error]')) {
                const detail = resp.replace('[LLM-Error]', '').trim().split('\n')[0];
                return `I wasn't able to complete that request right now.\n\n_${detail}_`;
              }
              if (!resp.startsWith("{") && !resp.startsWith("{'" )) return resp.trim();
            }
            // 3. Streamed tokens collected so far
            if (accumulated.trim()) return accumulated.trim();
            return 'Sorry, I could not generate a response right now.';
          })();
          set((s) => ({
            conversation: s.conversation.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: finalText, meta: {
                    confidence: typeof confidence === 'number' ? confidence : undefined,
                    critic_score: typeof critic_score === 'number' ? critic_score : undefined,
                    raw: result,
                  } }
                : m,
            ),
          }));
          // ── Auto-route content to media layers ───────────────────────
          const content = finalText || accumulated;
          _IMG_RE.lastIndex = 0; _VID_RE.lastIndex = 0; _AUD_RE.lastIndex = 0;
          const imgM = content.match(_IMG_RE);
          const vidM = content.match(_VID_RE);
          const audM = content.match(_AUD_RE);
          imgM?.forEach((u) => get().pushImage(u.trim()));
          vidM?.forEach((u) => get().pushVideo(u.trim()));
          audM?.forEach((u) => get().pushAudio(u.trim()));
          if (!imgM && !vidM && !audM && content.trim().length > 20) {
            get().pushTextHighlight(content.trim().slice(0, 500));
          }
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
