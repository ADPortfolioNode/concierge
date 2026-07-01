import React, { useMemo, useState } from 'react';
import { parseStepSummaries, truncateText } from '@/components/tasks/taskDisplayUtils';

interface Props {
  summary: string;
}

const STEP_PREVIEW_CHARS = 220;
const SINGLE_PREVIEW_CHARS = 360;

const ResultSummaryBlock: React.FC<Props> = ({ summary }) => {
  const [expanded, setExpanded] = useState(false);
  const steps = useMemo(() => parseStepSummaries(summary), [summary]);
  const isLong =
    summary.length > SINGLE_PREVIEW_CHARS || steps.some((s) => s.body.length > STEP_PREVIEW_CHARS);

  return (
    <div style={{ marginTop: 16, padding: 14, background: '#F0FDF4', border: '1px solid rgba(5,150,105,0.2)', borderRadius: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#059669', marginBottom: 10 }}>
        Result
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {steps.map((step, index) => (
          <div key={`${step.label}-${index}`}>
            {steps.length > 1 ? (
              <div style={{ fontSize: 12, fontWeight: 700, color: '#047857', marginBottom: 4 }}>{step.label}</div>
            ) : null}
            <p style={{ margin: 0, fontSize: 14, color: '#065F46', lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
              {expanded ? step.body : truncateText(step.body, steps.length > 1 ? STEP_PREVIEW_CHARS : SINGLE_PREVIEW_CHARS)}
            </p>
          </div>
        ))}
      </div>
      {isLong ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          style={{
            marginTop: 10,
            padding: 0,
            border: 'none',
            background: 'none',
            color: '#059669',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          {expanded ? 'Show less' : 'Show full summary'}
        </button>
      ) : null}
    </div>
  );
};

export default ResultSummaryBlock;