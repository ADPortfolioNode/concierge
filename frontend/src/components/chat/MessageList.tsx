import React, { useEffect, useRef } from 'react';
import { ConversationMessage } from '@/types/domain';
import MessageBubble from './MessageBubble';

interface Props {
  messages: ConversationMessage[];
}

const MessageList: React.FC<Props> = ({ messages }) => {
  const listRef = useRef<HTMLDivElement | null>(null);
  const prevLenRef = useRef<number>(messages.length);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    // auto-scroll to bottom when new message appended
    if (messages.length !== prevLenRef.current) {
      // small timeout to wait for layout
      setTimeout(() => {
        el.scrollTop = el.scrollHeight;
      }, 10);
    }
    prevLenRef.current = messages.length;
  }, [messages]);

  if (!messages || messages.length === 0) {
    // first-load system prompt
    return (
      <div ref={listRef} style={{ padding: 16, overflow: 'auto', height: '100%' }}>
        <MessageBubble
          msg={{
            id: 'welcome',
            role: 'system',
            content: 'Welcome. I\'m ready when you are. What would you like to work on today?',
            timestamp: new Date().toISOString(),
            media: null,
          }}
        />
      </div>
    );
  }

  return (
    <div ref={listRef} style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      {messages.map((m) => (
        <MessageBubble key={m.id} msg={m} />
      ))}
    </div>
  );
};

export default MessageList;
