import React from 'react';

export interface AccordionBadgeProps {
  id: string;
  label: string;
  hint?: string;
  tone?: 'default' | 'success' | 'warn' | 'muted';
  active: boolean;
  open: boolean;
  onToggle: () => void;
  children?: React.ReactNode;
}

const TONE_STYLES: Record<NonNullable<AccordionBadgeProps['tone']>, { border: string; bg: string; color: string }> = {
  default: { border: '#BFDBFE', bg: '#F0F8FF', color: '#2563EB' },
  success: { border: 'rgba(5,150,105,0.35)', bg: '#F0FDF4', color: '#059669' },
  warn: { border: 'rgba(220,38,38,0.25)', bg: '#FEF2F2', color: '#B91C1C' },
  muted: { border: '#E2E8F0', bg: '#F8FAFC', color: '#64748B' },
};

const AccordionBadge: React.FC<AccordionBadgeProps> = ({
  label,
  hint,
  tone = 'default',
  active,
  open,
  onToggle,
  children,
}) => {
  const palette = TONE_STYLES[tone];
  return (
    <div className={`accordion-badge ${open || active ? 'accordion-badge--open' : ''}`}>
      <button
        type="button"
        className={`accordion-badge__trigger ${active ? 'accordion-badge__trigger--active' : ''}`}
        onClick={onToggle}
        aria-expanded={open || active}
        style={{
          borderColor: open || active ? palette.color : palette.border,
          background: open || active ? palette.bg : '#FFFFFF',
          color: palette.color,
        }}
      >
        <span className="accordion-badge__label">{label}</span>
        {hint ? <span className="accordion-badge__hint">{hint}</span> : null}
        <span className="accordion-badge__chevron" aria-hidden>
          {open || active ? '−' : '+'}
        </span>
      </button>
      {open && children ? <div className="accordion-badge__panel accordion-badge__panel--inline">{children}</div> : null}
    </div>
  );
};

export default AccordionBadge;