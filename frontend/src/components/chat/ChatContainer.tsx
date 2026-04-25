import React, { useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TimelineHeader from '../TimelineHeader';
import AssistantRiver from '@/components/river/AssistantRiver';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

// ── concierge panel header ────────────────────────────────────────────────
const ConciergeHeader: React.FC = () => (
  <div
    style={{
      padding: '10px 14px 8px',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      background: 'rgba(0,0,0,0.3)',
      flexShrink: 0,
    }}
  >
    <div
      aria-label="Online"
      role="img"
      style={{
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: '#7c6af7',
        boxShadow: '0 0 6px #7c6af7',
        flexShrink: 0,
      }}
    />
    <div>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#c4b8ff', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
        Concierge
      </div>
      <div aria-live="polite" style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
        I'm ready to help
      </div>
    </div>
  </div>
);

const ChatContainer: React.FC = () => {
  const messages = useAppStore((s) => s.conversation);
  const taskTree = useAppStore((s) => s.taskTree);
  const selectedRiverNode = useAppStore((s) => s.selectedRiverNode);
  const setConversation = useAppStore((s) => s.setConversation);
  const setSelectedRiverNode = useAppStore((s) => s.setSelectedRiverNode);

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
      {/* concierge branding header */}
      <ConciergeHeader />
      {/* timeline thread header */}
      <TimelineHeader />
      {taskTree ? (
        <AssistantRiver
          tree={taskTree}
          selectedNode={selectedRiverNode}
          onSelectNode={setSelectedRiverNode}
        />
      ) : null}
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
