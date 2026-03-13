import React, { useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TimelineHeader from '../TimelineHeader';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

const ChatContainer: React.FC = () => {
  const messages = useAppStore((s) => s.conversation);
  const setConversation = useAppStore((s) => s.setConversation);

  // compute the provider/error of the most recent assistant message
  const lastMsg = messages.length ? messages[messages.length - 1] : null;
  const llmProvider = lastMsg?.meta?.llm?.provider;
  const llmError = lastMsg?.meta?.llm?.error;

  useEffect(() => {
    fetchConversation()
      .then((res) => {
        const data = (res as any)?.data;
        if (Array.isArray(data) && data.length > 0) {
          setConversation(data);
        }
      })
      .catch(() => {/* silently ignore — server may be cold-starting */});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* timeline thread header */}
      <TimelineHeader />
      {/* provider indicator header */}
      {(llmProvider || llmError) && (
        <div style={{ padding: '4px 8px', background: '#1f2937', color: '#9ca3af', fontSize: 12 }}>
          Provider: {llmProvider || 'unknown'}
          {llmError && <> – {llmError}</>}
        </div>
      )}
      <div style={{ flex: '1 1 auto', minHeight: 0 }}>
        <MessageList messages={messages} />
      </div>
      <div style={{ flex: '0 0 auto' }}>
        <MessageInput />
      </div>
    </div>
  );
};

export default ChatContainer;
