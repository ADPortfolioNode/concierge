import React from 'react';
import { ConversationMessage } from '@/types/domain';

interface Props {
  msg: ConversationMessage;
}

const MetaLine: React.FC<{ meta?: ConversationMessage['meta'] }> = ({ meta }) => {
  if (!meta) return null;
  const parts: string[] = [];
  if (typeof meta.confidence === 'number') parts.push(`Confidence: ${Math.round(meta.confidence * 100)}%`);
  if (typeof meta.critic_score === 'number') parts.push(`Critic: ${meta.critic_score}`);
  return <div style={{ fontSize: '12px', opacity: 0.7, marginTop: 6 }}>{parts.join(' • ')}</div>;
};

const MessageBubble: React.FC<Props> = ({ msg }) => {
  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: isSystem ? 'center' : isUser ? 'flex-end' : 'flex-start',
    padding: '8px 0',
  };

  const bubbleStyle: React.CSSProperties = {
    maxWidth: '78%',
    background: isSystem ? 'transparent' : 'rgba(255,255,255,0.04)',
    color: 'var(--color-text, #e6e6e6)',
    border: isSystem ? 'none' : '1px solid rgba(255,255,255,0.06)',
    padding: isSystem ? 0 : '12px 14px',
    borderRadius: 6,
    fontSize: 14,
    lineHeight: '1.4',
  };

  return (
    <div style={containerStyle}>
      <div style={bubbleStyle} aria-label={`message-${msg.id}`}>
        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
        {!isSystem && <MetaLine meta={msg.meta} />}
        {msg.timestamp && (
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 6 }}>{new Date(msg.timestamp).toLocaleString()}</div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
