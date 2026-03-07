import React from 'react';
import { useAppStore } from '@/state/appStore';

const ErrorBanner: React.FC = () => {
  const error = useAppStore((s) => s.error);
  const setError = useAppStore((s) => s.setError);

  if (!error) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: '#b71c1c',
        color: '#fff',
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 -2px 8px rgba(0,0,0,0.4)',
      }}
      role="alert"
    >
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, marginRight: 8 }} title={error ?? undefined}>{error}</span>
      <button
        onClick={() => setError(null)}
        style={{
          background: 'transparent',
          border: 'none',
          color: '#fff',
          fontWeight: 'bold',
          cursor: 'pointer',
        }}
        aria-label="Dismiss error"
      >
        ✕
      </button>
    </div>
  );
};

export default ErrorBanner;