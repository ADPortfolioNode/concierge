import React from 'react';

interface StackProps {
  children: React.ReactNode;
  direction?: 'row' | 'column';
  gap?: string;
}

const Stack: React.FC<StackProps> = ({ children, direction = 'column', gap }) => {
  const style: React.CSSProperties = {
    display: 'flex',
    flexDirection: direction,
    gap,
  };
  return <div style={style}>{children}</div>;
};

export default Stack;