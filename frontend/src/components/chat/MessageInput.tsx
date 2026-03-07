import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/state/appStore';
import FileUpload, { type FileContext } from './FileUpload';
import MediaPreview from './MediaPreview';

const MAX_LINES = 6;

const MessageInput: React.FC = () => {
  const [value, setValue] = useState('');
  const [attachment, setAttachment] = useState<FileContext | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showUploader, setShowUploader] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const loading = useAppStore((s) => s.loading);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const draftMessage = useAppStore((s) => s.draftMessage);
  const setDraft = useAppStore((s) => s.setDraft);

  // When a sample prompt is clicked from any page, it sets draftMessage in the
  // store.  We mirror it into local state and focus the textarea.
  useEffect(() => {
    if (draftMessage) {
      setValue(draftMessage);
      setDraft('');
      textareaRef.current?.focus();
    }
  }, [draftMessage, setDraft]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '0px';
    const desired = Math.min(el.scrollHeight, 24 * MAX_LINES);
    el.style.height = desired + 'px';
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!loading) {
          const text = value.trim();
          // Build message — optionally prepend a file-context reference.
          let outgoing = text;
          if (attachment) {
            const ref = `[file:${attachment.upload_id}/${attachment.filename}]`;
            outgoing = outgoing ? `${ref}\n${outgoing}` : ref;
          }
          if (outgoing) {
            sendMessage(outgoing);
            setValue('');
            setAttachment(null);
            setShowUploader(false);
          }
        }
      }
    },
    [value, loading, sendMessage, attachment]
  );

  const handleUpload = useCallback((ctx: FileContext) => {
    setAttachment(ctx);
    setUploadError(null);
    setShowUploader(false);
  }, []);

  return (
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.03)', padding: 12 }}>
      {/* Attachment preview */}
      {attachment && (
        <div style={{ marginBottom: 8 }}>
          <MediaPreview context={attachment} onRemove={() => setAttachment(null)} />
        </div>
      )}

      {/* Inline file-uploader (shown when 📎 is clicked) */}
      {showUploader && !attachment && (
        <div style={{ marginBottom: 8 }}>
          <FileUpload
            onUpload={handleUpload}
            onError={(msg) => { setUploadError(msg); setShowUploader(false); }}
          />
          {uploadError && (
            <div style={{ color: '#e06c75', fontSize: 12, marginTop: 4 }}>{uploadError}</div>
          )}
        </div>
      )}

      {/* Input row */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6 }}>
        {/* Attach button */}
        <button
          onClick={() => { setShowUploader((x) => !x); setUploadError(null); }}
          disabled={loading || !!attachment}
          title="Attach a file"
          style={{
            background: 'none',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 6,
            color: showUploader ? '#7c6af7' : 'rgba(255,255,255,0.5)',
            cursor: loading || attachment ? 'not-allowed' : 'pointer',
            fontSize: 18,
            padding: '4px 8px',
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          📎
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={loading ? 'Sending...' : 'Message — Enter to send, Shift+Enter for newline'}
          disabled={loading}
          rows={1}
          style={{
            flex: 1,
            resize: 'none',
            background: 'transparent',
            color: 'var(--color-text, #e6e6e6)',
            border: '1px solid rgba(255,255,255,0.1)',
            padding: 10,
            borderRadius: 6,
            fontSize: 14,
          }}
        />

        {/* Send button */}
        <button
          onClick={() => {
            const text = value.trim();
            let outgoing = text;
            if (attachment) {
              const ref = `[file:${attachment.upload_id}/${attachment.filename}]`;
              outgoing = outgoing ? `${ref}\n${outgoing}` : ref;
            }
            if (outgoing && !loading) {
              sendMessage(outgoing);
              setValue('');
              setAttachment(null);
              setShowUploader(false);
            }
          }}
          disabled={loading || (!value.trim() && !attachment)}
          title="Send message"
          style={{
            background: loading || !value.trim() ? 'rgba(124,106,247,0.2)' : '#7c6af7',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            cursor: loading || !value.trim() ? 'not-allowed' : 'pointer',
            fontSize: 16,
            padding: '6px 12px',
            lineHeight: 1,
            flexShrink: 0,
            transition: 'background 0.15s',
          }}
        >
          ↑
        </button>
      </div>

      <div style={{ marginTop: 6, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
        {loading && (
          <div style={{ fontSize: 12, opacity: 0.8, marginRight: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#7c6af7', animation: 'pulse 1s ease-in-out infinite' }} />
            Streaming…
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageInput;
