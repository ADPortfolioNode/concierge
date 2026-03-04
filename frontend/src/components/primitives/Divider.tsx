import React from 'react';

interface DividerProps {
  vertical?: boolean;
}

const Divider: React.FC<DividerProps> = ({ vertical = false }) => (
  <div
    style={{
      width: vertical ? '1px' : '100%',
      height: vertical ? '100%' : '1px',
      background: 'var(--color-accent)',
    }}
  />
);

export default Divider;