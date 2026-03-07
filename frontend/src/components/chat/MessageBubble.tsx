import React, { useState } from 'react';
import { ConversationMessage } from '@/types/domain';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';

interface Props {
  msg: ConversationMessage;
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
const IMAGE_URL_RE =
  /https?:\/\/\S+?(?:\.(?:png|jpg|jpeg|gif|webp|svg|avif))(?:\?\S*)?|https?:\/\/(?:picsum\.photos|i\.imgur\.com|images\.unsplash\.com)\S*/gi;

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
  const segments = splitContentIntoSegments(content);
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
      {segments.map((seg, i) =>
        seg.kind === 'image' ? (
          <InlineImage key={i} src={seg.value} />
        ) : (
          <span key={i} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'break-word', wordBreak: 'break-word' }}>
            {seg.value}
          </span>
        ),
      )}
      {isStreaming && <StreamingCursor />}
    </div>
  );
};

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
        <RichContent content={msg.content || (isStreaming ? '' : '…')} isStreaming={isStreaming} />
        {/* Render attached media (image/video/audio) */}
        {msg.media && msg.media.type !== 'none' && msg.media.url && (
          <div style={{ marginTop: 8 }}>
            <MediaRenderer media={{ type: msg.media.type, url: msg.media.url }} />
          </div>
        )}
        {!isSystem && !isStreaming && <MetaLine meta={msg.meta} />}
        {msg.timestamp && !isStreaming && (
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 6 }}>{new Date(msg.timestamp).toLocaleString()}</div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
