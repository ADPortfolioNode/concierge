import React, { useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import PageMetaBar from '../PageMetaBar';
import WorkflowStatusFeed from './WorkflowStatusFeed';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

const ChatContainer: React.FC = () => {
  const messages = useAppStore((s) => s.conversation);
  const loading = useAppStore((s) => s.loading);
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const setConversation = useAppStore((s) => s.setConversation);

  useEffect(() => {
    fetchConversation()
      .then((res) => {
        const data = (res as any)?.data;
        if (Array.isArray(data) && data.length > 0) {
          setConversation(data);
        }
      })
      .catch(() => {});
  }, [setConversation]);

  const status = loading ? 'Working…' : taskThreadId ? 'Orchestrating…' : 'Ready to help';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFFFF' }}>
      <div
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid #DBEAFE',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          flexShrink: 0,
          background: '#F8FAFF',
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>Concierge</div>
        <div aria-live="polite" style={{ fontSize: 11, color: '#64748B' }}>{status}</div>
      </div>
      <PageMetaBar compact />
      <WorkflowStatusFeed />
      <div style={{ flex: '1 1 auto', minHeight: 0 }}>
        <MessageList messages={messages} />
      </div>
      <MessageInput />
    </div>
  );
};

export default ChatContainer;