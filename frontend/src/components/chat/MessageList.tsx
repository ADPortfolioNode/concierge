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

  // Aggregate consecutive assistant messages into a single bubble so the
  // Concierge appears as a single conversant reply (magazine-style summary).
  const displayMessages: typeof messages = [] as any;
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    // start a new aggregate for assistant messages
    if (m.role === 'assistant') {
      let agg = { ...m } as any;
      // merge following assistant messages
      let j = i + 1;
      while (j < messages.length && messages[j].role === 'assistant') {
        const nxt = messages[j];
        // concatenate content with separation
        agg.content = `${agg.content}\n\n${nxt.content}`;
        // prefer the later meta (assume final summary at the end)
        agg.meta = nxt.meta || agg.meta;
        // if media exists in later messages, keep the latest media
        agg.media = nxt.media || agg.media;
        j++;
      }
      displayMessages.push(agg);
      i = j - 1;
    } else {
      displayMessages.push(m);
    }
  }

  return (
    <div ref={listRef} style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      {displayMessages.map((m) => (
        <MessageBubble key={m.id} msg={m} collapseCounter={collapseCounter} />
      ))}
    </div>
  );
};

export default MessageList;
