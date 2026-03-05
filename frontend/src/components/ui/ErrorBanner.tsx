import React from 'react';
import { useAppStore } from '@/state/appStore';

const ErrorBanner: React.FC = () => {
  const error = useAppStore((s) => s.error);
  const setError = useAppStore((s) => s.setError);

  if (!error) return null;

  return (
    <div
      style={{
        background: '#b71c1c',
        color: '#fff',
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
      role="alert"
    >
      <span>{error}</span>
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