import React, { useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TimelineHeader from '../TimelineHeader';
import AssistantRiver from '@/components/river/AssistantRiver';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

// ── concierge panel header ────────────────────────────────────────────────
const ConciergeHeader: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const taskTree = useAppStore((s) => s.taskTree);
  const isOrchestrating = !!taskThreadId;
  const childCount = taskTree?.children?.length ?? 0;
  const statusLabel = isOrchestrating
    ? childCount > 0
      ? `Orchestrating ${childCount} task${childCount !== 1 ? 's' : ''}…`
      : 'Orchestrating…'
    : 'Ready to help';

  return (
    <div
      style={{
        padding: '10px 16px 10px',
        borderBottom: '1px solid #DBEAFE',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        background: 'linear-gradient(135deg, #EFF6FF 0%, #F0F8FF 100%)',
        flexShrink: 0,
      }}
    >
      <div
        aria-label={isOrchestrating ? 'Active' : 'Online'}
        role="img"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: isOrchestrating ? '#22C55E' : '#38BDF8',
          boxShadow: isOrchestrating ? '0 0 8px #22C55E' : '0 0 6px #38BDF8',
          flexShrink: 0,
          animation: isOrchestrating ? 'concierge-pulse 1.4s ease-in-out infinite' : 'none',
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
          Concierge
          <span style={{ fontSize: 11, fontWeight: 500, color: '#64748B', marginLeft: 6 }}>AI Assistant</span>
        </div>
        <div
          aria-live="polite"
          style={{
            fontSize: 10,
            color: isOrchestrating ? '#16A34A' : '#38BDF8',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            fontWeight: 600,
            transition: 'color 0.3s',
          }}
        >
          {statusLabel}
        </div>
      </div>
      {isOrchestrating && (
        <div
          title={`Thread: ${taskThreadId}`}
          style={{
            fontSize: 9,
            color: '#38BDF8',
            fontFamily: 'monospace',
            letterSpacing: '0.04em',
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            borderRadius: 6,
            padding: '2px 6px',
            maxWidth: 80,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {taskThreadId?.slice(0, 8)}…
        </div>
      )}
    </div>
  );
};

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFFFF' }}>
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
