import React, { useEffect } from 'react';
import { useAppStore } from '@/state/appStore';

const TimelineHeader: React.FC = () => {
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const fetchTimeline = useAppStore((s) => s.fetchTimeline);
  const selectedTaskMeta = useAppStore((s) => s.selectedTaskMeta);
  const selectTimelineTask = useAppStore((s) => s.selectTimelineTask);

  // refresh every 12 seconds or when conversation length changes
  const convoLen = useAppStore((s) => s.conversation.length);
  useEffect(() => {
    fetchTimeline();
    const iv = setInterval(fetchTimeline, 12000);
    return () => clearInterval(iv);
  }, [fetchTimeline, convoLen]);

  if (!timelinePlan || !Array.isArray(timelinePlan.tasks)) {
    return null;
  }

  return (
    <div style={{ background: '#111827', color: '#9ca3af', padding: '4px 8px', fontSize: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img
          src="/api/v1/concierge/timeline/graph"
          alt="timeline graph"
          style={{ maxHeight: 40 }}
        />
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {(timelinePlan.tasks || []).map((t: any, idx: number) => (
            <button
              key={idx}
              onClick={() => selectTimelineTask(t)}
              style={{
                background: '#374151',
                border: 'none',
                borderRadius: 4,
                padding: '2px 6px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              {t.title || t.instructions || `task ${idx + 1}`}
            </button>
          ))}
        </div>
      </div>
      {selectedTaskMeta && (
        <div
          style={{
            marginTop: 6,
            background: '#1f2937',
            border: '1px solid #374151',
            borderRadius: 6,
            padding: 8,
            fontSize: 11,
          }}
        >
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0, color: '#e5e7eb' }}>
            {JSON.stringify(selectedTaskMeta, null, 2)}
          </pre>
          <button
            onClick={() => selectTimelineTask(null)}
            style={{
              marginTop: 4,
              background: 'transparent',
              border: '1px solid #6b7280',
              borderRadius: 4,
              padding: '2px 6px',
              color: '#6b7280',
              cursor: 'pointer',
              fontSize: 10,
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
};

export default TimelineHeader;
