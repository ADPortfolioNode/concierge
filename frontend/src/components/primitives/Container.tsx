import React from 'react';

interface ContainerProps {
  children: React.ReactNode;
  maxWidth?: string;
}

const Container: React.FC<ContainerProps> = ({ children, maxWidth = '1200px' }) => (
  <div style={{ margin: '0 auto', maxWidth }}>{children}</div>
);

export default Container;