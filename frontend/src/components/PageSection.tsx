import React from 'react';

interface PageSectionProps {
  title: string;
  children: React.ReactNode;
}

const PageSection: React.FC<PageSectionProps> = ({ title, children }) => (
  <section className="page-section">
    <h2 className="section-heading">{title}</h2>
    {children}
  </section>
);

export default PageSection;
