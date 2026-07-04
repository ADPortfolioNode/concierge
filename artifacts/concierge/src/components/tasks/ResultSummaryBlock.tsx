import React, { useMemo, useState } from 'react';
import RichTextWithImages from '@/components/media/RichTextWithImages';
import { parseStepSummaries, truncateText } from '@/components/tasks/taskDisplayUtils';
import { extractImageUrls } from '@/utils/imageContent';

interface Props {
  summary: string;
  embedded?: boolean;
}

const STEP_PREVIEW_CHARS = 220;
const SINGLE_PREVIEW_CHARS = 360;

const ResultSummaryBlock: React.FC<Props> = ({ summary, embedded = false }) => {
  const [expanded, setExpanded] = useState(false);
  const steps = useMemo(() => parseStepSummaries(summary), [summary]);
  const isLong =
    summary.length > SINGLE_PREVIEW_CHARS || steps.some((s) => s.body.length > STEP_PREVIEW_CHARS);

  return (
    <div
      style={
        embedded
          ? { padding: 0, background: 'transparent', border: 'none' }
          : { marginTop: 16, padding: 14, background: '#F0FDF4', border: '1px solid rgba(5,150,105,0.2)', borderRadius: 10 }
      }
    >
      {!embedded ? (
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#059669', marginBottom: 10 }}>
          Result
        </div>
      ) : null}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {steps.map((step, index) => (
          <div key={`${step.label}-${index}`}>
            {steps.length > 1 ? (
              <div style={{ fontSize: 12, fontWeight: 700, color: '#047857', marginBottom: 4 }}>{step.label}</div>
            ) : null}
            <div style={{ margin: 0, fontSize: 14, color: '#065F46', lineHeight: 1.65 }}>
              {(() => {
                const imageUrls = extractImageUrls(step.body);
                const textOnly = imageUrls.reduce(
                  (text, url) => text.split(url).join(''),
                  step.body,
                ).replace(/\n{2,}/g, '\n').trim();
                const preview = expanded
                  ? step.body
                  : truncateText(textOnly || step.body, steps.length > 1 ? STEP_PREVIEW_CHARS : SINGLE_PREVIEW_CHARS);
                const imageBlock = imageUrls.length > 0 ? `\n\n${imageUrls.join('\n')}` : '';
                return (
                  <RichTextWithImages
                    content={expanded ? step.body : `${preview}${imageBlock}`}
                    textStyle={{ color: '#065F46', lineHeight: 1.65 }}
                  />
                );
              })()}
            </div>
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