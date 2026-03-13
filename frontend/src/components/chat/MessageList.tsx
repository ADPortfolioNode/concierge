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

  // Scroll to bottom whenever new messages arrive or streaming state changes.
  // The `messages` prop may be a new array reference even when its contents
  // haven’t changed, so we track the previous length and only update the
  // collapse counter when the length actually increases (or streamingId
  // toggles) to avoid an effect loop.
  const prevLen = useRef(messages.length);
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (atBottom || streamingId) {
      el.scrollTop = el.scrollHeight;
    }
    // only bump when messages array got longer or streamingId changed
    if (messages.length !== prevLen.current) {
      prevLen.current = messages.length;
      setCollapseCounter((c) => c + 1);
    } else if (streamingId) {
      // if no new message but streaming started/continues we still collapse
      setCollapseCounter((c) => c + 1);
    }
  }, [messages.length, streamingId]);

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
