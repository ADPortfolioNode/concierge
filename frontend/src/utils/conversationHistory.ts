/**
 * conversationHistory.ts
 *
 * Industry-standard hybrid memory pattern:
 *   - Server side : ChromaDB on a named Docker volume (persistent RAG store)
 *   - Browser side: IndexedDB (with localStorage fallback) for full per-session
 *                   conversation history so the chat thread survives page refreshes
 *                   and allows the backend to receive the entire context on every call.
 *
 * This module provides a simple async API over IndexedDB.  If IndexedDB is
 * unavailable (e.g. private-browsing restrictions in some browsers) it falls
 * back to localStorage so the feature degrades gracefully rather than failing.
 */

import { ConversationMessage } from '../types/domain';

const DB_NAME = 'concierge_memory';
const STORE_NAME = 'conversation';
const KEY = 'history';
const LS_KEY = 'concierge_conversation_history';

// ── IndexedDB helpers ──────────────────────────────────────────────────────

// Singleton DB connection — reused across calls to avoid repeated open/close
// overhead on every read or write operation.
let _dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_dbPromise) return _dbPromise;
  _dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => {
      _dbPromise = null; // allow retry on failure
      reject(req.error);
    };
  });
  return _dbPromise;
}

async function idbGet(db: IDBDatabase): Promise<ConversationMessage[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).get(KEY);
    req.onsuccess = () => resolve(Array.isArray(req.result) ? req.result : []);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(db: IDBDatabase, messages: ConversationMessage[]): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const req = tx.objectStore(STORE_NAME).put(messages, KEY);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function idbClear(db: IDBDatabase): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const req = tx.objectStore(STORE_NAME).delete(KEY);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ── localStorage fallback helpers ─────────────────────────────────────────

function lsGet(): ConversationMessage[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function lsPut(messages: ConversationMessage[]): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(messages));
  } catch {
    // storage quota exceeded — silently ignore
  }
}

function lsClear(): void {
  try {
    localStorage.removeItem(LS_KEY);
  } catch {
    // ignore
  }
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Load the saved conversation history from IndexedDB (or localStorage
 * fallback).  Returns an empty array when nothing has been stored yet.
 */
export async function loadHistory(): Promise<ConversationMessage[]> {
  try {
    const db = await openDB();
    return await idbGet(db);
  } catch {
    return lsGet();
  }
}

/**
 * Persist the full conversation history to IndexedDB (or localStorage
 * fallback).  Call this whenever the conversation array changes.
 */
export async function saveHistory(messages: ConversationMessage[]): Promise<void> {
  try {
    const db = await openDB();
    await idbPut(db, messages);
  } catch {
    lsPut(messages);
  }
}

/**
 * Wipe all stored conversation history from both IndexedDB and localStorage.
 * This is the "Clear memory" action — browser-side complement to flushing the
 * ChromaDB collection on the server.
 */
export async function clearHistory(): Promise<void> {
  lsClear();
  try {
    const db = await openDB();
    await idbClear(db);
  } catch {
    // IndexedDB unavailable — localStorage was already cleared above
  }
}
