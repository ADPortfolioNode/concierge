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

  const tasks = Array.isArray(timelinePlan?.tasks)
    ? timelinePlan.tasks
    : Array.isArray(timelinePlan?.plan?.tasks)
    ? timelinePlan.plan.tasks
    : [];
  // Use an explicit graph version token to force reload when timelinePlan changes
  // Use a relative URL so system images are requested from the current origin.
  const vParam = encodeURIComponent((timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now()));
  const graphPath = `/api/v1/concierge/timeline/graph?v=${vParam}`;
  const graphSrc = makeApiUrl(graphPath);
  const placeholderPath = `${import.meta.env.BASE_URL || '/'}timeline-graph-placeholder.svg`;
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
      <div className="timeline-hero-card">
        <div className="timeline-hero-preview">
          <button onClick={() => setExpanded(true)} className="timeline-hero-image-button">
            <img
              src={graphUrl}
              alt="timeline hero"
              className="timeline-hero-image"
              loading="lazy"
              decoding="async"
              onError={(e) => { (e.currentTarget as HTMLImageElement).src = placeholderPath; }}
            />
          </button>

          <div className="timeline-hero-task-strip">
            {tasks.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
                No Concierge timeline tasks are available yet — ask Concierge to create a plan or add a goal.
              </div>
            ) : (
              tasks.map((t: any) => (
                <button key={t.task_id} onClick={() => { setSelected(t); selectTimelineTask(t); }} className={`timeline-task-pill ${selected?.task_id === t.task_id ? 'timeline-task-pill--active' : ''}`}>
                  <div className="timeline-task-title">{t.title || 'Untitled'}</div>
                  <div className="timeline-task-copy">{(t.instructions || '').slice(0, 60)}</div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Expanded overlay (unchanged) */}
      {expanded && (
        <div role="dialog" aria-label="Timeline fullscreen" style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(6,6,12,0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }} onClick={() => setExpanded(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{ width: '100%', height: '100%', maxWidth: '100%', maxHeight: '100%', display: 'flex', flexDirection: 'column', gap: 18, borderRadius: 12 }}>
            <div style={{ width: '100%', flex: '0 0 auto', minHeight: 0, borderRadius: 8, overflow: 'hidden', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <img
                src={graphUrl}
                alt="timeline large"
                style={{ width: '100%', height: '100%', minHeight: 260, objectFit: 'contain' }}
                loading="lazy"
                decoding="async"
                onError={(e) => { (e.currentTarget as HTMLImageElement).src = placeholderPath; }}
              />
            </div>
            <div style={{ width: '100%', flex: '1 1 auto', overflow: 'auto', background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: 12 }}>
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
