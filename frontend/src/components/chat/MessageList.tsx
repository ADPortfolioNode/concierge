import React, { useEffect, useRef } from 'react';
import { ConversationMessage } from '@/types/domain';
import MessageBubble from './MessageBubble';
import { useAppStore } from '@/state/appStore';

interface Props {
  messages: ConversationMessage[];
}

const MessageList: React.FC<Props> = ({ messages }) => {
  const listRef = useRef<HTMLDivElement | null>(null);
  const streamingId = useAppStore((s) => s.streamingId);
  const [collapseCounter, setCollapseCounter] = React.useState(0);

  // Scroll to bottom whenever messages are added OR the streaming bubble grows
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (atBottom || streamingId) {
      el.scrollTop = el.scrollHeight;
    }
    // bump counter to tell bubbles to collapse their meta panels
    setCollapseCounter((c) => c + 1);
  }, [messages, streamingId]);

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
        <MessageBubble key={m.id} msg={m} collapseCounter={collapseCounter} />
      ))}
    </div>
  );
};

export default MessageList;
