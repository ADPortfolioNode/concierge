// domain-specific types
export interface MediaRef {
  type: 'image' | 'video' | 'audio' | 'text' | 'none';
  url: string | null;
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  media?: MediaRef | null;
  meta?: {
    critic_score?: number;
    confidence?: number;
    priority?: number;
    raw?: Record<string, unknown> | null;
    // provider used and any fallback/error message from the LLM
    llm?: {
      provider?: string | null;
      error?: string | null;
    };
  } | null;
}
