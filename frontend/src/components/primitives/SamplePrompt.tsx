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
  /** Optional label shown above the prompt text (e.g. "Try this →") */
  label?: string;
  /** Visual style: 'chip' (compact pill) | 'card' (padded block) */
  variant?: 'chip' | 'card';
  /** Navigate to home route after injecting so the chat is visible */
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
          background: 'rgba(124,106,247,0.12)',
          border: '1px solid rgba(124,106,247,0.35)',
          borderRadius: 99,
          color: '#c4b8ff',
          cursor: 'pointer',
          fontSize: 13,
          padding: '4px 14px',
          transition: 'background 0.15s, border-color 0.15s',
          maxWidth: '100%',
          overflow: 'hidden',
          minWidth: 0,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'rgba(124,106,247,0.25)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'rgba(124,106,247,0.12)';
        }}
      >
        <span style={{ opacity: 0.7, flexShrink: 0 }}>↗</span>
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
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 8,
        padding: '12px 16px',
        width: '100%',
        boxSizing: 'border-box',
        transition: 'background 0.15s, border-color 0.15s',
        textAlign: 'left',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.background = 'rgba(124,106,247,0.1)';
        el.style.borderColor = 'rgba(124,106,247,0.4)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.background = 'rgba(255,255,255,0.03)';
        el.style.borderColor = 'rgba(255,255,255,0.08)';
      }}
    >
      {label && (
        <div style={{ fontSize: 11, color: '#7c6af7', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </div>
      )}
      <div style={{ fontSize: 13, color: '#d4d0ff', lineHeight: 1.5 }}>"{text}"</div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 6 }}>Click to use →</div>
    </button>
  );
};

export default SamplePrompt;
