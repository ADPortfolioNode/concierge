import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConversationMessage } from '@/types/domain';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';

interface Props {
  msg: ConversationMessage;
  // incrementing value that tells the bubble to close its meta panel when it
  // changes (e.g. a new message arrived)
  collapseCounter?: number;
}

// ---------------------------------------------------------------------------
// Streaming cursor
// ---------------------------------------------------------------------------

// Blinking cursor shown while the assistant bubble is still streaming
const StreamingCursor: React.FC = () => (
  <span
    aria-hidden
    style={{
      display: 'inline-block',
      width: 2,
      height: '1em',
      background: 'currentColor',
      marginLeft: 2,
      verticalAlign: 'text-bottom',
      animation: 'blink 0.9s step-start infinite',
    }}
  />
);

// Inject the keyframe once (idempotent)
if (typeof document !== 'undefined' && !document.getElementById('_stream-blink')) {
  const s = document.createElement('style');
  s.id = '_stream-blink';
  s.textContent = '@keyframes blink { 50% { opacity: 0 } }';
  document.head.appendChild(s);
}

// ---------------------------------------------------------------------------
// Inline image rendering helpers
// ---------------------------------------------------------------------------

/** Regex that matches http(s) URLs ending with an image extension OR known
 *  image-hosting domains (picsum.photos, i.imgur.com, etc.) */
// Match absolute http(s) image URLs, known image hosts, or local `/media/images/...` and `media/images/...` paths
const IMAGE_URL_RE =
  /(?:https?:\/\/\S+?(?:\.(?:png|jpg|jpeg|gif|webp|svg|avif))(?:\?\S*)?|https?:\/\/(?:picsum\.photos|i\.imgur\.com|images\.unsplash\.com)\S*|\/?media\/images\/\S+?(?:\.(?:png|jpg|jpeg|gif|webp|svg|avif))(?:\?\S*)?)/gi;

interface Segment {
  kind: 'text' | 'image';
  value: string;
}

function splitContentIntoSegments(content: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;
  IMAGE_URL_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = IMAGE_URL_RE.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ kind: 'text', value: content.slice(lastIndex, match.index) });
    }
    segments.push({ kind: 'image', value: match[0] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    segments.push({ kind: 'text', value: content.slice(lastIndex) });
  }
  return segments.length > 0 ? segments : [{ kind: 'text', value: content }];
}

/** A single inline image with a subtle loading/error state */
const InlineImage: React.FC<{ src: string }> = ({ src }) => {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>('loading');
  return (
    <div style={{ margin: '10px 0' }}>
      {status !== 'error' ? (
        <img
          src={src}
          alt="Generated image"
          onLoad={() => setStatus('loaded')}
          onError={() => setStatus('error')}
          style={{
            maxWidth: '100%',
            maxHeight: 400,
            borderRadius: 6,
            display: 'block',
            opacity: status === 'loading' ? 0.4 : 1,
            transition: 'opacity 0.25s',
            border: '1px solid rgba(255,255,255,0.1)',
            resize: 'both',
            overflow: 'auto',
          }}
        />
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 12px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6,
            fontSize: 12,
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          🖼️ <span>Image could not be loaded</span>
          <a href={src} target="_blank" rel="noopener noreferrer" style={{ color: '#6366F1', marginLeft: 4 }}>
            Open ↗
          </a>
        </div>
      )}
    </div>
  );
};

/** Render message content, turning embedded image URLs into <img> elements */
const RichContent: React.FC<{ content: string; isStreaming: boolean }> = ({ content, isStreaming }) => {
  const navigate = useNavigate();
  const segments = useMemo(() => splitContentIntoSegments(content), [content]);
  const hasImages = segments.some((s) => s.kind === 'image');

  if (!hasImages) {
    return (
      <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'break-word', wordBreak: 'break-word' }}>
        {content}
        {isStreaming && <StreamingCursor />}
      </div>
    );
  }
  return (
    <div>
      {segments.map((seg, i) => {
        if (seg.kind === 'image') {
          const src = seg.value;
          // If the image is a locally persisted media image, do NOT render
          // it inline. Instead, push it into the MediaStage store so it is
          // shown in the media player only. Recognize local media by the
          // `/media/images/` or `media/images/` path which may be used by backend.
          if (src.includes('/media/images/') || src.includes('media/images/')) {
            const normalizedSrc = src.startsWith('/') ? src : `/${src}`;
            return <InlineImage key={i} src={normalizedSrc} />;
          }
          return <InlineImage key={i} src={src} />;
        }
        return (
          <span key={i} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'break-word', wordBreak: 'break-word' }}>
            {seg.value}
          </span>
        );
      })}
      {isStreaming && <StreamingCursor />}
      {/** show provider badge for LLM if available */}
      {/** meta is not directly available here so parent will render new badge */}
    </div>
  );
};

const MetaPanel: React.FC<{ meta?: ConversationMessage['meta']; collapseCounter?: number }> = ({ meta, collapseCounter }) => {
  const [open, setOpen] = useState(false);
  // whenever parent indicates a new message batch, collapse the panel
  useEffect(() => {
    if (open) {
      setOpen(false);
    }
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
  // optionally show provider badge in collapsed header
  if (typeof meta.confidence === 'number') scoreParts.push(`${Math.round(meta.confidence * 100)}% confidence`);
  if (typeof meta.critic_score === 'number') scoreParts.push(`critic ${meta.critic_score}`);
  const label = scoreParts.length > 0 ? scoreParts.join(' · ') : 'details';

  return (
    <div style={{ marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 5 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open ? 'true' : 'false'}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'rgba(255,255,255,0.35)', fontSize: 11, padding: '2px 0',
          display: 'flex', alignItems: 'center', gap: 5,
        }}
      >
        <span style={{ fontSize: 8, lineHeight: 1 }}>{open ? '▾' : '▸'}</span>
        {label}
      </button>
      {open && (
        <div style={{
          marginTop: 6, padding: '8px 10px',
          background: 'rgba(0,0,0,0.22)', borderRadius: 6,
          fontSize: 11, color: 'rgba(255,255,255,0.55)', lineHeight: 1.7,
        }}>
          {keyPoints.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600, marginBottom: 2 }}>Key points</div>
              {keyPoints.map((pt: string, i: number) => (
                <div key={i} style={{ paddingLeft: 10 }}>{pt}</div>
              ))}
            </div>
          )}
          {recommendations.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600, marginBottom: 2 }}>Recommendations</div>
              {recommendations.map((r: string, i: number) => (
                <div key={i} style={{ paddingLeft: 10 }}>{r}</div>
              ))}
            </div>
          )}
          {refined && (
            <div style={{ marginBottom: 6 }}>
              <span style={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Summary: </span>{refined}
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <span style={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>Risks: </span>
              {risks.join(', ')}
            </div>
          )}
          {provider && (
            <div style={{ marginTop: 8 }}>
              <span style={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>LLM Provider:</span> {provider}
              {errorMsg && <div style={{ paddingLeft: 10, color: 'rgba(255,255,255,0.6)' }}>{errorMsg}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
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
      ? 'rgba(124,106,247,0.18)'
      : 'rgba(255,255,255,0.04)',
    color: 'var(--color-text, #e6e6e6)',
    border: isSystem
      ? 'none'
      : isUser
      ? '1px solid rgba(124,106,247,0.35)'
      : '1px solid rgba(255,255,255,0.06)',
    padding: isSystem ? 0 : '12px 14px',
    borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
    fontSize: 14,
    lineHeight: '1.4',
  };

  return (
    <div style={containerStyle}>
      <div style={bubbleStyle} aria-label={`message-${msg.id}`}>
        {/* If the message meta contains structured cards, render as
            a magazine-style compact card grid (titles only). Clicking a
            card opens a full-width overlay with the full content. */}
        {(() => {
          const raw = (msg.meta && (msg.meta.raw as any)) || null;
          const structured = raw?.structured || raw;
          const cards = structured?.cards || structured?.results || null;
          if (Array.isArray(cards) && cards.length > 0) {
            return <MagazineLayout cards={cards} msg={msg} />;
          }
          return <RichContent content={msg.content || (isStreaming ? '' : '…')} isStreaming={isStreaming} />;
        })()}
        {/* indicate which LLM provider generated this reply */}
        {msg.meta?.llm?.provider && (
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>
            Provider: {msg.meta.llm.provider}
            {msg.meta.llm.error && ` (${msg.meta.llm.error})`}
          </div>
        )}
        {/* Render attached media (image/video/audio) */}
        {msg.media && msg.media.type !== 'none' && msg.media.url && (
          <div style={{ marginTop: 8 }}>
            <MediaRenderer media={{ type: msg.media.type, url: msg.media.url }} />
            <button
              onClick={() => {
                setActiveMedia(msg.media?.url || null);
                navigate('/media');
              }}
              style={{
                marginTop: 8,
                background: 'rgba(124,106,247,0.18)',
                border: '1px solid rgba(124,106,247,0.35)',
                color: '#dfe6ff',
                borderRadius: 6,
                padding: '8px 10px',
                cursor: 'pointer',
              }}
            >
              Open media page
            </button>
          </div>
        )}
        {!isSystem && !isStreaming && <MetaPanel meta={msg.meta} />}
        {msg.timestamp && !isStreaming && (
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 6 }}>{new Date(msg.timestamp).toLocaleString()}</div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;

// ---------------------------------------------------------------------------
// Magazine layout: compact titled cards that expand to a full-width overlay
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
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.04)',
              cursor: 'pointer',
              color: 'var(--color-text, #e6e6e6)',
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
            <div style={{ color: 'rgba(255,255,255,0.28)', fontSize: 11 }}>{(c.use_cases || []).length ? (c.use_cases || []).length : ''}</div>
          </button>
        ))}
      </div>

      {/* expanded overlay */}
      {expanded && (
        <div
          style={{
            marginTop: 12,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 10,
            padding: 14,
            color: 'rgba(255,255,255,0.92)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>{expanded.title || expanded.name}</div>
              {expanded.estimated_use_cases && (
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', marginTop: 4 }}>
                  Estimated use cases: {(expanded.estimated_use_cases || []).join(', ')}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {expanded.media_url && (
                <button
                  onClick={() => pushImage && pushImage(expanded.media_url)}
                  style={{ padding: '6px 8px', borderRadius: 6, background: 'rgba(124,106,247,0.18)', border: '1px solid rgba(124,106,247,0.35)', color: '#dfe6ff', cursor: 'pointer' }}
                >
                  Open media
                </button>
              )}
              <button onClick={() => setExpanded(null)} style={{ padding: '6px 8px', borderRadius: 6, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.8)', cursor: 'pointer' }}>
                Close
              </button>
            </div>
          </div>

          <div style={{ color: 'rgba(255,255,255,0.86)', lineHeight: 1.6 }}>
            {expanded.summary && <div style={{ marginBottom: 12 }}>{expanded.summary}</div>}
            {expanded.content && <div style={{ whiteSpace: 'pre-wrap' }}>{expanded.content}</div>}
          </div>
        </div>
      )}
    </div>
  );
};
