let baseUrl = '';

export function setApiBaseUrl(url: string) {
  baseUrl = url.replace(/\/$/, '');
}

export function getApiBaseUrl(): string {
  return baseUrl;
}

interface ApiEnvelope<T> {
  status: string;
  data: T;
  timestamp?: string;
  request_id?: string;
  errors?: unknown;
  meta?: Record<string, unknown>;
}

interface MessageData {
  id?: string;
  role?: string;
  content?: string | unknown;
  timestamp?: string;
  meta?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function sendMessage(
  message: string,
  history: ChatMessage[] = []
): Promise<string> {
  const url = `${baseUrl}/api/v1/concierge/message`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`Request failed: ${res.status} ${text}`);
  }

  const envelope: ApiEnvelope<MessageData> = await res.json();

  if (envelope.status === 'error') {
    throw new Error('Backend returned an error response');
  }

  const msgData = envelope.data;
  const content = msgData?.content;

  if (typeof content === 'string') return content;
  if (content != null) return String(content);

  throw new Error('No content in response');
}

export interface Task {
  id: string;
  task_id?: string;
  type?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  goal?: string;
  description?: string;
  progress?: number;
  children?: Task[];
  [key: string]: unknown;
}

export async function fetchTasks(): Promise<Task[]> {
  const url = `${baseUrl}/api/v1/tasks`;
  const res = await fetch(url, {
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch tasks: ${res.status}`);
  }

  const envelope: ApiEnvelope<Task[] | Record<string, unknown>> = await res.json();

  if (envelope.status === 'error') {
    throw new Error('Backend returned an error for tasks');
  }

  const data = envelope.data;
  if (Array.isArray(data)) return data as Task[];
  return [];
}

export async function fetchTaskStatus(taskId: string): Promise<Task | null> {
  const url = `${baseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/status`;
  const res = await fetch(url, {
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) return null;

  const envelope: ApiEnvelope<Task> = await res.json();
  if (envelope.status === 'error') return null;
  return envelope.data ?? null;
}

export async function fetchHealth(): Promise<boolean> {
  try {
    const url = `${baseUrl}/api/_health`;
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}
