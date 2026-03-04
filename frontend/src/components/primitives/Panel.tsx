import React from 'react';

interface PanelProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const Panel: React.FC<PanelProps> = ({ children, style }) => {
  return <div style={{ padding: 'var(--space-4)', ...style }}>{children}</div>;
};

export default Panel;