import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConversationMessage } from '@/types/domain';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';
import RichTextWithImages from '@/components/media/RichTextWithImages';

interface Props {
  msg: ConversationMessage;
  collapseCounter?: number;
}

const RichContent: React.FC<{ content: string; isStreaming: boolean }> = ({ content, isStreaming }) => (
  <RichTextWithImages content={content} isStreaming={isStreaming} />
);

// ---------------------------------------------------------------------------
// MetaPanel
// ---------------------------------------------------------------------------

const MetaPanel: React.FC<{ meta?: ConversationMessage['meta']; collapseCounter?: number }> = ({ meta, collapseCounter }) => {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (open) setOpen(false);
  }, [collapseCounter]);
  if (!meta) return null;

  const hasScores = typeof meta.confidence === 'number' || typeof meta.critic_score === 'number';
  const raw = meta.raw as any;
  const provider = meta.llm?.provider;
  const errorMsg = meta.llm?.error;
  const structured = raw?.structured ?? raw?.final?.structured;
  const keyPoints: string[] = structured?.key_points ?? [];
  const recommendations: string[] = structured?.recommendations ?? [];
  const risks: string[] = structured?.risks ?? [];
  const refined: string = structured?.refined_recommendation ?? '';
  const hasDetails = keyPoints.length > 0 || recommendations.length > 0 || risks.length > 0 || refined;

  if (!hasScores && !hasDetails && !meta.llm) return null;

  const scoreParts: string[] = [];
  if (typeof meta.confidence === 'number') scoreParts.push(`${Math.round(meta.confidence * 100)}% confidence`);
  if (typeof meta.critic_score === 'number') scoreParts.push(`critic ${meta.critic_score}`);
  const label = scoreParts.length > 0 ? scoreParts.join(' · ') : 'details';

  return (
    <div style={{ marginTop: 8, borderTop: '1px solid #DBEAFE', paddingTop: 5 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open ? 'true' : 'false'}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: '#94A3B8', fontSize: 11, padding: '2px 0',
          display: 'flex', alignItems: 'center', gap: 5,
        }}
      >
        <span style={{ fontSize: 8, lineHeight: 1 }}>{open ? '▾' : '▸'}</span>
        {label}
      </button>
      {open && (
        <div style={{
          marginTop: 6, padding: '8px 10px',
          background: '#F0F8FF', borderRadius: 6, border: '1px solid #DBEAFE',
          fontSize: 11, color: '#475569', lineHeight: 1.7,
        }}>
          {keyPoints.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={{ color: '#334155', fontWeight: 600, marginBottom: 2 }}>Key points</div>
              {keyPoints.map((pt: string, i: number) => (
                <div key={i} style={{ paddingLeft: 10 }}>{pt}</div>
              ))}
            </div>
          )}
          {recommendations.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={{ color: '#334155', fontWeight: 600, marginBottom: 2 }}>Recommendations</div>
              {recommendations.map((r: string, i: number) => (
                <div key={i} style={{ paddingLeft: 10 }}>{r}</div>
              ))}
            </div>
          )}
          {refined && (
            <div style={{ marginBottom: 6 }}>
              <span style={{ color: '#334155', fontWeight: 600 }}>Summary: </span>{refined}
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <span style={{ color: '#334155', fontWeight: 600 }}>Risks: </span>
              {risks.join(', ')}
            </div>
          )}
          {provider && (
            <div style={{ marginTop: 8 }}>
              <span style={{ color: '#334155', fontWeight: 600 }}>LLM Provider:</span> {provider}
              {errorMsg && <div style={{ paddingLeft: 10, color: '#64748B' }}>{errorMsg}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// MessageBubble
// ---------------------------------------------------------------------------

const roleLabel = (role: ConversationMessage['role']) => {
  if (role === 'user') return 'You';
  if (role === 'assistant') return 'Concierge';
  return 'System';
};

const MessageBubble: React.FC<Props> = ({ msg, collapseCounter }) => {
  const navigate = useNavigate();
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);
  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';
  const streamingId = useAppStore((s) => s.streamingId);
  const isStreaming = streamingId === msg.id;

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: isSystem ? 'center' : isUser ? 'flex-end' : 'flex-start',
    padding: '8px 0',
  };

  const bubbleStyle: React.CSSProperties = {
    maxWidth: '78%',
    background: isSystem
      ? 'transparent'
      : isUser
      ? '#DBEAFE'
      : '#FFFFFF',
    color: '#0F172A',
    border: isSystem
      ? 'none'
      : isUser
      ? '1px solid #93C5FD'
      : '1px solid #DBEAFE',
    padding: isSystem ? 0 : '12px 14px',
    borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
    fontSize: 14,
    lineHeight: '1.4',
    boxShadow: isSystem ? 'none' : '0 1px 4px rgba(37,99,235,0.06)',
  };

  return (
    <div style={containerStyle}>
      <div style={bubbleStyle} aria-label={`message-${msg.id}`} data-message-role={msg.role}>
        {!isSystem && (
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: isUser ? '#1D4ED8' : '#64748B',
              marginBottom: 6,
            }}
          >
            {roleLabel(msg.role)}
          </div>
        )}
        {(() => {
          const raw = (msg.meta && (msg.meta.raw as any)) || null;
          const structured = raw?.structured || raw;
          const cards = structured?.cards || structured?.results || null;
          if (Array.isArray(cards) && cards.length > 0) {
            return <MagazineLayout cards={cards} msg={msg} />;
          }
          return <RichContent content={msg.content || (isStreaming ? '' : '…')} isStreaming={isStreaming} />;
        })()}
        {msg.meta?.llm?.provider && (
          <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>
            Provider: {msg.meta.llm.provider}
            {msg.meta.llm.error && ` (${msg.meta.llm.error})`}
          </div>
        )}
        {msg.media && msg.media.type !== 'none' && msg.media.url && (
          <div style={{ marginTop: 8 }}>
            <MediaRenderer media={{ type: msg.media.type, url: msg.media.url, overlay_text: null, mime_type: null }} />
            <button
              type="button"
              onClick={() => {
                setActiveMedia(msg.media?.url || null);
                navigate('/media');
              }}
              style={{
                marginTop: 6,
                background: 'none',
                border: 'none',
                color: '#2563EB',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
                padding: 0,
                textDecoration: 'underline',
              }}
            >
              View in Media
            </button>
          </div>
        )}
        {!isSystem && !isStreaming && <MetaPanel meta={msg.meta} collapseCounter={collapseCounter} />}
        {msg.timestamp && !isStreaming && (
          <div style={{ fontSize: 11, opacity: 0.5, marginTop: 6, color: '#64748B' }}>{new Date(msg.timestamp).toLocaleString()}</div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;

// ---------------------------------------------------------------------------
// Magazine layout
// ---------------------------------------------------------------------------
const MagazineLayout: React.FC<{ cards: any[]; msg: ConversationMessage }> = ({ cards, msg }) => {
  const pushImage = useAppStore((s) => s.pushImage);
  const [expanded, setExpanded] = useState<any | null>(null);

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
        {cards.map((c: any, i: number) => (
          <button
            key={c.id || i}
            onClick={() => setExpanded(c)}
            style={{
              textAlign: 'left',
              padding: '10px 12px',
              borderRadius: 8,
              background: '#F0F8FF',
              border: '1px solid #DBEAFE',
              cursor: 'pointer',
              color: '#0F172A',
              fontSize: 13,
              minHeight: 48,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
            aria-label={`card-${c.id || i}`}
          >
            <div style={{ flex: 1, paddingRight: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {c.title || c.name || `Option ${i + 1}`}
            </div>
            <div style={{ color: '#94A3B8', fontSize: 11 }}>{(c.use_cases || []).length ? (c.use_cases || []).length : ''}</div>
          </button>
        ))}
      </div>

      {/* expanded overlay */}
      {expanded && (
        <div
          style={{
            marginTop: 12,
            background: '#F0F8FF',
            border: '1px solid #BFDBFE',
            borderRadius: 10,
            padding: 14,
            color: '#0F172A',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#0F172A' }}>{expanded.title || expanded.name}</div>
              {expanded.estimated_use_cases && (
                <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                  Estimated use cases: {(expanded.estimated_use_cases || []).join(', ')}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {expanded.media_url && (
                <button
                  onClick={() => pushImage && pushImage(expanded.media_url)}
                  style={{ padding: '6px 8px', borderRadius: 6, background: '#EFF6FF', border: '1px solid #93C5FD', color: '#2563EB', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
                >
                  Open media
                </button>
              )}
              <button onClick={() => setExpanded(null)} style={{ padding: '6px 8px', borderRadius: 6, background: '#F8FAFF', border: '1px solid #DBEAFE', color: '#475569', cursor: 'pointer' }}>
                Close
              </button>
            </div>
          </div>

          <div style={{ color: '#334155', lineHeight: 1.6 }}>
            {expanded.summary && <div style={{ marginBottom: 12 }}>{expanded.summary}</div>}
            {expanded.content && <div style={{ whiteSpace: 'pre-wrap' }}>{expanded.content}</div>}
          </div>
        </div>
      )}
    </div>
  );
};
