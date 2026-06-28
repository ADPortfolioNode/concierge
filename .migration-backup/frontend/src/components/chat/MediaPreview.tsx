/**
 * MediaPreview — shows a compact summary card for an uploaded FileContext.
 *
 * Displays the filename, type badge, file size, and (optionally) an
 * expandable extracted-text preview.
 */

import React, { useState } from 'react';
import type { FileContext } from './FileUpload';

interface MediaPreviewProps {
  context: FileContext;
  onRemove?: () => void;
}

function mimeLabel(mime: string): { label: string; icon: string } {
  if (mime.startsWith('image/')) return { label: 'Image', icon: '🖼️' };
  if (mime.startsWith('audio/')) return { label: 'Audio', icon: '🎵' };
  if (mime.startsWith('video/')) return { label: 'Video', icon: '🎬' };
  if (mime === 'application/pdf') return { label: 'PDF', icon: '📄' };
  if (mime.includes('wordprocessingml') || mime === 'application/msword')
    return { label: 'DOCX', icon: '📝' };
  if (mime === 'text/csv') return { label: 'CSV', icon: '📊' };
  if (mime === 'application/json') return { label: 'JSON', icon: '🗃️' };
  if (mime.startsWith('text/')) return { label: 'Text', icon: '📃' };
  return { label: 'File', icon: '📁' };
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

const MediaPreview: React.FC<MediaPreviewProps> = ({ context, onRemove }) => {
  const [expanded, setExpanded] = useState(false);
  const { label, icon } = mimeLabel(context.mime ?? '');
  const hasText = !!context.extracted_text?.trim();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        background: '#F0F8FF',
        border: '1px solid #BFDBFE',
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: 12,
        color: '#0F172A',
        maxWidth: 360,
        position: 'relative',
        resize: 'both',
        overflow: 'auto',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <span style={{ fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#0F172A' }}>
          {context.filename}
        </span>
        <span
          style={{
            background: '#DBEAFE',
            color: '#2563EB',
            borderRadius: 3,
            padding: '1px 5px',
            fontSize: 10,
            fontWeight: 600,
          }}
        >
          {label}
        </span>
        {onRemove && (
          <button
            onClick={onRemove}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#94A3B8',
              fontSize: 14,
              lineHeight: 1,
              padding: '0 2px',
            }}
            aria-label="Remove attachment"
          >
            ×
          </button>
        )}
      </div>

      {/* Meta row */}
      <div style={{ color: '#94A3B8', fontSize: 11, display: 'flex', gap: 10 }}>
        <span>{fmtBytes(context.size ?? 0)}</span>
        <span style={{ fontFamily: 'monospace', opacity: 0.7 }}>{context.upload_id?.slice(0, 8)}</span>
      </div>

      {/* Expandable text preview */}
      {hasText && (
        <>
          <button
            onClick={() => setExpanded((x) => !x)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#2563EB',
              fontSize: 11,
              padding: 0,
              textAlign: 'left',
            }}
          >
            {expanded ? '▲ Hide text preview' : '▼ Show text preview'}
          </button>
          {expanded && (
            <pre
              style={{
                background: '#EFF6FF',
                border: '1px solid #DBEAFE',
                borderRadius: 4,
                padding: '6px 8px',
                fontSize: 11,
                color: '#334155',
                maxHeight: 160,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: 0,
              }}
            >
              {(context.extracted_text ?? '').slice(0, 800)}
              {(context.extracted_text?.length ?? 0) > 800 && (
                <span style={{ opacity: 0.5 }}>{'\n…(truncated)'}</span>
              )}
            </pre>
          )}
        </>
      )}
    </div>
  );
};

export default MediaPreview;
