import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/state/appStore';
import { makeApiUrl } from '@/config/activeServer';

const TimelineHero: React.FC = () => {
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const fetchTimeline = useAppStore((s) => s.fetchTimeline);
  const selectTimelineTask = useAppStore((s) => s.selectTimelineTask);
  const [selected, setSelected] = useState<any | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [graphVersion, setGraphVersion] = useState<string>(String(Date.now()));

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);
  useEffect(() => {
    // start SSE streaming for live updates
    (async () => {
      try {
        (window as any).__START_TIMELINE_STREAM__ = true;
        const start = (await import('@/state/appStore')).useAppStore.getState().startTimelineStream;
        start && start();
      } catch (e) {
        // ignore
      }
    })();
    return () => {
      try {
        const stop = (require('@/state/appStore').useAppStore.getState().stopTimelineStream);
        stop && stop();
      } catch (e) {}
    };
  }, []);

  const tasks = Array.isArray(timelinePlan?.tasks) ? timelinePlan.tasks : [];
  // Use an explicit graph version token to force reload when timelinePlan changes
  // Use a relative URL so system images are requested from the current origin.
  const vParam = encodeURIComponent((timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now()));
  const graphPath = `/api/v1/concierge/timeline/graph?v=${vParam}`;
  const graphSrc = makeApiUrl(graphPath);
  const placeholderPng = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII=';
  const graphUrl = graphSrc;

  useEffect(() => {
    // bump the graph version whenever timelinePlan changes so the browser
    // fetches the updated PNG rather than serving a cached copy.
    try {
      const v = (timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now());
      setGraphVersion(String(v));
    } catch (e) {
      setGraphVersion(String(Date.now()));
    }
  }, [timelinePlan]);

  return (
    <>
      <div style={{ marginBottom: 18 }}>
        {/* Full-width hero row */}
        <div style={{ width: '100%', borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.03)', background: 'linear-gradient(90deg, rgba(124,106,247,0.04), rgba(79,176,198,0.01))' }}>
            <button onClick={() => setExpanded(true)} style={{ display: 'block', width: '100%', padding: 0, border: 'none', background: 'transparent', cursor: 'zoom-in' }}>
              <img
                src={graphUrl}
                alt="timeline hero"
                style={{ width: '100%', height: 160, objectFit: 'cover', display: 'block' }}
                loading="lazy"
                decoding="async"
                onError={(e) => { (e.currentTarget as HTMLImageElement).src = placeholderPng; }}
              />
            </button>

          {/* One-row horizontal task strip */}
          <div style={{ display: 'flex', gap: 8, padding: '10px 12px', alignItems: 'center', overflowX: 'auto', whiteSpace: 'nowrap' }}>
            {tasks.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>No plan yet — set a goal or ask the assistant to create a plan.</div>
            ) : (
              tasks.map((t: any) => (
                <button key={t.task_id} onClick={() => { setSelected(t); selectTimelineTask(t); }} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', minWidth: 180, background: selected?.task_id === t.task_id ? '#7c6af7' : 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)', color: selected?.task_id === t.task_id ? '#fff' : '#e2e8f0', padding: '8px 12px', borderRadius: 8, cursor: 'pointer', marginRight: 4 }}>
                  <div style={{ fontWeight: 800, fontSize: 13, textAlign: 'left' }}>{t.title || 'Untitled'}</div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4 }}>{(t.instructions || '').slice(0, 60)}</div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Expanded overlay (unchanged) */}
      {expanded && (
        <div role="dialog" aria-label="Timeline fullscreen" style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(6,6,12,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }} onClick={() => setExpanded(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{ width: '92%', height: '86%', display: 'flex', gap: 18, borderRadius: 12 }}>
              <div style={{ flex: '0 0 64%', height: '100%', borderRadius: 8, overflow: 'hidden', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img
                  src={graphUrl}
                  alt="timeline large"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  loading="lazy"
                  decoding="async"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).src = placeholderPng; }}
                />
              </div>
            <div style={{ flex: 1, height: '100%', overflow: 'auto', background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>Sacred Timeline</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', marginBottom: 12 }}>Includes Concierge activity and live updates</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                {tasks.map((t: any) => (
                  <button key={t.task_id} onClick={() => { setSelected(t); selectTimelineTask(t); }} style={{ background: selected?.task_id === t.task_id ? '#7c6af7' : 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)', color: selected?.task_id === t.task_id ? '#fff' : '#e2e8f0', padding: '8px 10px', borderRadius: 8, cursor: 'pointer' }}>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>{t.title || 'Untitled'}</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{(t.instructions || '').slice(0, 80)}</div>
                  </button>
                ))}
              </div>

              {selected ? (
                <div style={{ marginTop: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 8, padding: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800 }}>{selected.title}</div>
                      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{selected.task_id}</div>
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{selected.status || 'unknown'}</div>
                  </div>

                  <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 8 }}>{selected.instructions}</div>

                  {Array.isArray(selected.depends_on) && selected.depends_on.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', fontWeight: 700, marginBottom: 6 }}>Depends on</div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {selected.depends_on.map((d: string) => (
                          <div key={d} style={{ fontFamily: 'monospace', fontSize: 12, background: 'rgba(255,255,255,0.03)', padding: '6px 8px', borderRadius: 6 }}>{d}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ marginTop: 12, color: 'rgba(255,255,255,0.4)' }}>Select a task to see details.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TimelineHero;
