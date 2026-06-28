import { create } from 'zustand';
import { ConversationMessage } from '../types/domain';
import * as ConciergeAPI from '@/api/conciergeService';
import { fetchTaskTree, TaskTree } from '@/api/taskService';
import { ACTIVE_API_BASE, makeApiUrl } from '@/config/activeServer';
// Industry-standard hybrid memory pattern: persist conversation history in
// browser storage (IndexedDB with localStorage fallback) so the full chat
// thread survives page refreshes and can be sent to the backend on every call.
import { loadHistory, saveHistory, clearHistory } from '@/utils/conversationHistory';

export interface MediaItem {
  id: string;
  url: string;
  timestamp: string;
}

// Regexes shared with MediaStage for routing responses to the right layer
// Accept absolute http(s) image URLs and local `/media/images/*` or `media/images/*` paths
const _IMG_RE = /(?:https?:\/\/\S+?\.(?:png|jpg|jpeg|gif|webp|svg|avif)(?:\?\S*)?|https?:\/\/(?:picsum\.photos|i\.imgur\.com|images\.unsplash\.com)\S*|\/?media\/images\/\S+?\.(?:png|jpg|jpeg|gif|webp|svg|avif)(?:\?\S*)?)/gi;
const _VID_RE = /https?:\/\/\S+?\.(?:mp4|webm)(?:[?#]\S*)?/gi;
const _AUD_RE = /https?:\/\/\S+?\.(?:mp3|wav|m4a)(?:[?#]\S*)?/gi;

// Base API host for resolving local media paths (set via Vite envs)
const API_BASE = (ACTIVE_API_BASE || '').replace(/\/$/, '');

function _normalizeMediaUrl(url: string) {
  if (!url) return url;
  try {
    if (url.startsWith('/media') || url.startsWith('media/')) {
      return url.startsWith('/') ? url : `/${url}`;
    }
  } catch (e) {
    // ignore
  }
  return url;
}

function _normalizeUrlsInObject(obj: any) {
  if (!obj || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map((v) => _normalizeUrlsInObject(v));
  const out: any = {};
  for (const [k, v] of Object.entries(obj)) {
      if (typeof v === 'string' && (v.startsWith('/media') || v.startsWith('media/'))) {
      out[k] = _normalizeMediaUrl(v);
    } else if (typeof v === 'object' && v !== null) {
      out[k] = _normalizeUrlsInObject(v);
    } else {
      out[k] = v;
    }
  }
  return out;
}

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
  // timeline/header state
  timelinePlan: any | null;
  taskThreadId: string | null;
  taskTree: TaskTree | null;
  selectedRiverNode: any | null;
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
  // timeline actions
  setTimelinePlan: (plan: any) => void;
  setTaskTree: (tree: TaskTree | null) => void;
  setTaskThreadId: (id: string | null) => void;
  setSelectedTaskMeta: (meta: any) => void;
  setSelectedRiverNode: (meta: any) => void;
  clearTaskThread: () => void;
  pollTaskThreadStatus: (taskId: string) => Promise<void>;
  fetchTimeline: () => Promise<void>;
  fetchMedia: () => Promise<void>;
  selectTimelineTask: (task: any) => void;
  sendMessage: (input: string) => Promise<void>;
  /** Wipe browser-stored conversation history (IndexedDB + localStorage). */
  clearMemory: () => Promise<void>;
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
  taskThreadId: null,
  taskTree: null,
  selectedTaskMeta: null,
  selectedRiverNode: null,
  setError: (msg) => set({ error: msg }),
  setDraft: (text) => set({ draftMessage: text }),
  setConversation: (msgs) => {
    const normalized = Array.isArray(msgs) ? msgs.map((m) => _normalizeUrlsInObject(m)) : [];
    set({ conversation: normalized });
    // Persist to IndexedDB/localStorage so history survives page refreshes
    saveHistory(normalized).catch(() => { /* best-effort */ });
  },
  setActiveMedia: (url) => set({ activeMedia: _normalizeMediaUrl(url || '') || null }),
  appendMessage: (msg) => set((s) => {
    const updated = [...s.conversation, _normalizeUrlsInObject(msg)];
    saveHistory(updated).catch(() => { /* best-effort */ });
    return { conversation: updated };
  }),
  // timeline actions
  setTimelinePlan: (plan) => set({ timelinePlan: plan }),
  setTaskTree: (tree) => set({ taskTree: tree }),
  setTaskThreadId: (id) => set({ taskThreadId: id }),
  setSelectedTaskMeta: (meta) => set({ selectedTaskMeta: meta }),
  setSelectedRiverNode: (meta) => set({ selectedRiverNode: meta }),
  clearTaskThread: () => {
    if (typeof window !== 'undefined') {
      const poller = (window as any).__TASK_THREAD_POLLER__;
      if (poller) {
        clearInterval(poller);
        (window as any).__TASK_THREAD_POLLER__ = null;
      }
    }
    set({ taskThreadId: null, taskTree: null, selectedRiverNode: null });
  },
  pollTaskThreadStatus: async (taskId: string) => {
    if (typeof window === 'undefined') return;
    try {
      const tick = async () => {
        try {
          const tree = await fetchTaskTree(taskId);
          set({ taskTree: tree, taskThreadId: taskId });
          if (tree.status === 'done' || tree.status === 'completed' || tree.status === 'error' || tree.progress === 100) {
            const poller = (window as any).__TASK_THREAD_POLLER__;
            if (poller) {
              clearInterval(poller);
              (window as any).__TASK_THREAD_POLLER__ = null;
            }
          }
        } catch {
          // ignore temporary fetch failures
        }
      };
      if ((window as any).__TASK_THREAD_POLLER__) {
        clearInterval((window as any).__TASK_THREAD_POLLER__);
      }
      await tick();
      (window as any).__TASK_THREAD_POLLER__ = setInterval(tick, 2500);
    } catch {
      // ignore
    }
  },
  fetchTimeline: async () => {
    try {
      const plan = await ConciergeAPI.getTimeline();
      set({ timelinePlan: plan });
    } catch {
      // ignore
    }
  },
  fetchMedia: async () => {
    try {
      const res = await ConciergeAPI.getMedia();
      const list = res.data?.data || [];
      // normalize and push as imageLayers (preserve existing order)
      const imgs = Array.isArray(list) ? list.filter((m: any) => m.url && m.metadata?.mime_type?.startsWith('image') || m.url?.match(/\.(png|jpg|jpeg|gif|webp)$/i)).map((m: any) => ({ id: m.filename || `img-${Date.now()}`, url: _normalizeMediaUrl(m.url), timestamp: m.metadata?.created_at || m.mtime || new Date().toISOString() })) : [];
      if (imgs.length) {
        set((s) => ({ imageLayers: [...s.imageLayers, ...imgs].slice(-50) }));
      }
    } catch (e) {
      // ignore errors
    }
  },
  startTimelineStream: () => {
    if (typeof window === 'undefined') return;
    try {
      const es = new EventSource(makeApiUrl('/api/v1/concierge/timeline/stream'));
      (window as any).__TIMELINE_ES__ = es;
      es.onmessage = (ev) => {
        try {
          const parsed = JSON.parse(ev.data);
          if (parsed.type === 'plan') {
            const plan = parsed.plan || { tasks: [] };
            set({ timelinePlan: { ...plan, updated_at: new Date().toISOString() } });
          } else if (parsed.type === 'task_update') {
            const upd: any = parsed;
            set((s) => {
              const plan = s.timelinePlan || { tasks: [] } as any;
              const tasks = Array.isArray(plan.tasks) ? [...plan.tasks] : [];
              const idx = tasks.findIndex((t: any) => (t && t.task_id) === upd.task_id);
              if (idx >= 0) {
                tasks[idx] = {
                  ...tasks[idx],
                  ...(upd.task_name ? { title: upd.task_name } : {}),
                  ...(upd.status ? { status: upd.status } : {}),
                  ...(typeof upd.progress === 'number' ? { progress: upd.progress } : {}),
                  ...(upd.summary ? { summary: upd.summary } : {}),
                  manager_agent_id: upd.manager_agent_id || tasks[idx].manager_agent_id,
                };
              } else {
                // add a minimal task record if not present
                tasks.push({ task_id: upd.task_id, title: upd.task_name || upd.task_id, status: upd.status, progress: typeof upd.progress === 'number' ? upd.progress : undefined, summary: upd.summary });
              }
              const newPlan = { ...plan, tasks, updated_at: new Date().toISOString() };
              const selected = s.selectedTaskMeta && s.selectedTaskMeta.task_id === upd.task_id ? { ...s.selectedTaskMeta, ...(upd.summary ? { summary: upd.summary } : {}), ...(upd.status ? { status: upd.status } : {}), ...(typeof upd.progress === 'number' ? { progress: upd.progress } : {}) } : s.selectedTaskMeta;
              return { timelinePlan: newPlan, selectedTaskMeta: selected } as any;
            });
          }
        } catch (e) {
          // ignore bad event
        }
      };
      es.onerror = () => {
        try { es.close(); } catch (e) {}
      };
    } catch (e) {
      // ignore in non-browser env
    }
  },
  stopTimelineStream: () => {
    if (typeof window === 'undefined') return;
    const es = (window as any).__TIMELINE_ES__;
    if (es) {
      try { es.close(); } catch (e) {}
      (window as any).__TIMELINE_ES__ = null;
    }
  },
  selectTimelineTask: (task) => set({ selectedTaskMeta: task }),
  pushImage: (url) => set((s) => {
    const normalizedUrl = _normalizeMediaUrl(url);
    const existing = s.imageLayers.find((item) => item.url === normalizedUrl);
    if (existing) {
      return { activeMedia: normalizedUrl };
    }
    const item = { id: `img-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, url: normalizedUrl, timestamp: new Date().toISOString() };
    return { imageLayers: [...s.imageLayers, item], activeMedia: normalizedUrl };
  }),
  pushVideo: (url) => set((s) => {
    const normalizedUrl = _normalizeMediaUrl(url);
    const existing = s.videoLayers.find((item) => item.url === normalizedUrl);
    if (existing) {
      return {};
    }
    const item = { id: `vid-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, url: normalizedUrl, timestamp: new Date().toISOString() };
    return { videoLayers: [...s.videoLayers, item] };
  }),
  pushAudio: (url) => set((s) => {
    const normalizedUrl = _normalizeMediaUrl(url);
    const existing = s.audioLayers.find((item) => item.url === normalizedUrl);
    if (existing) {
      return {};
    }
    const item = { id: `aud-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, url: normalizedUrl, timestamp: new Date().toISOString() };
    return { audioLayers: [...s.audioLayers, item] };
  }),
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

    // Reset any existing task-river state before starting a new request.
    get().clearTaskThread();

    // Capture the history BEFORE adding the new messages so we only send
    // prior turns to the backend (hybrid memory: full context per call).
    const priorHistory = get().conversation.map((m) => ({ role: m.role, content: m.content }));

    set((s) => {
      const updated = [...s.conversation, userMsg, placeholderMsg];
      saveHistory(updated).catch(() => { /* best-effort */ });
      return { conversation: updated, loading: true, streamingId: assistantMsgId, error: null };
    });

    // if tests want to bypass SSE they can set window.USE_POST = true
    const usePost = Boolean((window as any).USE_POST);
    // record that sendMessage was invoked; tests can check this flag
    // The primary flow is now to send the message and then listen for updates on a WebSocket.
    try {
      // This now returns immediately with a thread_id if it's a background job
      const res = await ConciergeAPI.sendMessage(input, priorHistory);
      const result = res.data as any;
      const threadId = result.thread_id || result.data?.thread_id || null;
      const assistantResponse = result.data; // The full assistant message object

      // Update the placeholder with the initial response from the server
      set(s => {
        const updated = s.conversation.map(m => m.id === assistantMsgId ? { ...assistantResponse, id: assistantMsgId } : m);
        saveHistory(updated).catch(() => { /* best-effort */ });
        return { conversation: updated };
      });

      // If we got a threadId, it means a background task started.
      // We should connect to the WebSocket to get live updates for the task tree.
      if (threadId) {
        set({ taskThreadId: threadId });
        // The polling logic can be replaced by a WebSocket connection handler
        get().pollTaskThreadStatus(threadId).catch(() => {});
      }

    } catch (e) {
      const errText = e instanceof Error ? e.message : String(e);
      set(s => ({
        conversation: s.conversation.map(m => m.id === assistantMsgId ? { ...m, content: `⚠️ ${errText}` } : m),
        error: errText
      }));
    } finally {
      set({ loading: false, streamingId: null });
    }
  },

  // Wipe the browser-side conversation history from IndexedDB and localStorage,
  // and reset the in-memory conversation list (hybrid memory — browser side).
  clearMemory: async () => {
    await clearHistory();
    set({ conversation: [] });
  },
}));

// Restore conversation history from IndexedDB/localStorage on startup so the
// chat thread is preserved across page refreshes (hybrid memory — browser side).
if (typeof window !== 'undefined') {
  loadHistory().then((msgs) => {
    if (msgs.length > 0) {
      useAppStore.getState().setConversation(msgs);
    }
  }).catch(() => { /* best-effort — ignore storage errors */ });
}

// expose helper for tests to inspect store state
if (typeof window !== 'undefined') {
  // expose utility getters and the hook itself so tests can manipulate
  // conversation state directly without having to go through the network.
  (window as any).getAppStore = () => useAppStore.getState();
  (window as any).__APP_STORE__ = useAppStore.getState();
  useAppStore.subscribe((s) => {
    (window as any).__APP_STORE__ = s;
  });
  // the hook function allows tests to call actions, e.g. window.__APP_STORE__.appendMessage(...)
  (window as any).__APP_HOOK__ = useAppStore;
}
