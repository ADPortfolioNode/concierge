/**
 * SamplePrompt — a clickable prompt chip or card.
 *
 * Clicking injects the prompt text into the chat sidebar input via the
 * appStore `draftMessage` field and optionally navigates to the home route
 * so the user can immediately see the chat.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';

interface Props {
  text: string;
  label?: string;
  variant?: 'chip' | 'card';
  navigateToChat?: boolean;
}

const SamplePrompt: React.FC<Props> = ({
  text,
  label,
  variant = 'card',
  navigateToChat = true,
}) => {
  const setDraft = useAppStore((s) => s.setDraft);
  const navigate = useNavigate();

  const handleClick = () => {
    setDraft(text);
    if (navigateToChat) navigate('/');
  };

  if (variant === 'chip') {
    return (
      <button
        onClick={handleClick}
        title="Click to use this prompt"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#EFF6FF',
          border: '1px solid #BFDBFE',
          borderRadius: 99,
          color: '#1E40AF',
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 500,
          padding: '5px 14px',
          transition: 'background 0.15s, border-color 0.15s, transform 0.15s',
          maxWidth: '100%',
          overflow: 'hidden',
          minWidth: 0,
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget as HTMLButtonElement;
          el.style.background = '#DBEAFE';
          el.style.borderColor = '#93C5FD';
          el.style.transform = 'translateY(-1px)';
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLButtonElement;
          el.style.background = '#EFF6FF';
          el.style.borderColor = '#BFDBFE';
          el.style.transform = 'translateY(0)';
        }}
      >
        <span style={{ opacity: 0.5, flexShrink: 0, fontSize: 11 }}>↗</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>{text}</span>
      </button>
    );
  }

  // card variant
  return (
    <button
      onClick={handleClick}
      title="Click to use this prompt"
      style={{
        all: 'unset',
        display: 'block',
        cursor: 'pointer',
        background: '#FFFFFF',
        border: '1px solid #DBEAFE',
        borderRadius: 10,
        padding: '12px 16px',
        width: '100%',
        boxSizing: 'border-box',
        transition: 'background 0.15s, border-color 0.15s, box-shadow 0.15s',
        textAlign: 'left',
        boxShadow: '0 1px 4px rgba(37,99,235,0.05)',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.background = '#EFF6FF';
        el.style.borderColor = '#93C5FD';
        el.style.boxShadow = '0 4px 16px rgba(37,99,235,0.1)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.background = '#FFFFFF';
        el.style.borderColor = '#DBEAFE';
        el.style.boxShadow = '0 1px 4px rgba(37,99,235,0.05)';
      }}
    >
      {label && (
        <div style={{ fontSize: 11, color: '#2563EB', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </div>
      )}
      <div style={{ fontSize: 13, color: '#1E40AF', lineHeight: 1.5 }}>"{text}"</div>
      <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 6 }}>Click to use →</div>
    </button>
  );
};

export default SamplePrompt;
