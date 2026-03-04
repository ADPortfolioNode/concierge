import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/state/appStore';

const MAX_LINES = 6;

const MessageInput: React.FC = () => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const loading = useAppStore((s) => s.loading);
  const sendMessage = useAppStore((s) => s.sendMessage);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    // auto-expand
    el.style.height = '0px';
    const desired = Math.min(el.scrollHeight, 24 * MAX_LINES);
    el.style.height = desired + 'px';
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (value.trim() && !loading) {
          sendMessage(value.trim());
          setValue('');
        }
      }
    },
    [value, loading, sendMessage]
  );

  return (
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.03)', padding: 12 }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={loading ? 'Sending...' : 'Type your message and press Enter to send'}
        disabled={loading}
        rows={1}
        style={{
          width: '100%',
          resize: 'none',
          background: 'transparent',
          color: 'var(--color-text, #e6e6e6)',
          border: '1px solid rgba(255,255,255,0.04)',
          padding: 10,
          borderRadius: 6,
          fontSize: 14,
        }}
      />
      <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
        {loading && <div style={{ fontSize: 12, opacity: 0.8, marginRight: 8 }}>● Sending</div>}
      </div>
    </div>
  );
};

export default MessageInput;
