import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/state/appStore';

const apiBase = (import.meta as any).env?.VITE_API_URL || '';
function makeApiUrl(path: string) {
  if (apiBase && String(apiBase).trim()) {
    return `${String(apiBase).replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`;
  }
  return path;
}

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

  // if there's no plan yet, still show a compact header icon that can open dropdown
  const [open, setOpen] = useState(false);

  return (
    <div style={{ background: '#111827', color: '#9ca3af', padding: '6px 10px', fontSize: 12, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img src={`/api/v1/concierge/timeline/graph?v=${encodeURIComponent((timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now()))}`} alt="timeline graph" style={{ height: 36, cursor: 'pointer' }} onClick={() => setOpen((v) => !v)} />
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          {(timelinePlan?.tasks || []).slice(0, 4).map((t: any, idx: number) => (
            <button
              key={idx}
              onClick={() => selectTimelineTask(t)}
              style={{
                background: '#374151',
                border: 'none',
                borderRadius: 4,
                padding: '4px 8px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {t.title || t.instructions || `task ${idx + 1}`}
            </button>
          ))}
        </div>
        <button onClick={() => setOpen((v) => !v)} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>{open ? '▴' : '▾'}</button>
      </div>

      {open && (
        <div style={{ position: 'absolute', right: 10, top: '100%', marginTop: 8, background: '#0b1220', border: '1px solid #263244', borderRadius: 8, padding: 12, width: 540, zIndex: 60 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: '0 0 220px' }}>
              <img src={`/api/v1/concierge/timeline/graph?v=${encodeURIComponent((timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now()))}`} alt="timeline graph large" style={{ width: '100%', borderRadius: 6 }} />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#e6edf3' }}>Timeline</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
                {(timelinePlan?.tasks || []).map((t: any, idx: number) => (
                  <div key={t.task_id || idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button onClick={() => { selectTimelineTask(t); setOpen(false); }} style={{ background: 'transparent', border: 'none', color: '#cbd5e1', textAlign: 'left', cursor: 'pointer', padding: '6px 8px', borderRadius: 6 }}>
                      <div style={{ fontWeight: 700, fontSize: 13 }}>{t.title || `Task ${idx + 1}`}</div>
                      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{(t.instructions || '').slice(0, 100)}</div>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
          {selectedTaskMeta && (
            <div style={{ marginTop: 10, background: '#071025', padding: 8, borderRadius: 6 }}>
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0, color: '#e5e7eb', fontSize: 12 }}>{JSON.stringify(selectedTaskMeta, null, 2)}</pre>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <button onClick={() => selectTimelineTask(null)} style={{ background: 'transparent', border: '1px solid #233244', borderRadius: 6, padding: '6px 10px', color: '#9ca3af' }}>Close</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TimelineHeader;
