import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/state/appStore';
import { makeApiUrl } from '@/config/activeServer';

const PLACEHOLDER_SVG_DATA_URI = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6366f1" />
      <stop offset="100%" stop-color="#0ea5e9" />
    </linearGradient>
  </defs>
  <rect width="320" height="180" rx="20" fill="#111827" />
  <rect x="24" y="38" width="42" height="96" rx="12" fill="rgba(255,255,255,0.12)" />
  <rect x="88" y="18" width="42" height="116" rx="12" fill="rgba(255,255,255,0.18)" />
  <rect x="152" y="60" width="42" height="74" rx="12" fill="rgba(255,255,255,0.14)" />
  <rect x="216" y="24" width="42" height="110" rx="12" fill="rgba(255,255,255,0.16)" />
  <path d="M26 150 Q90 90 154 118 T292 70" fill="none" stroke="url(#grad)" stroke-width="10" stroke-linecap="round" />
  <text x="160" y="165" fill="#e2e8f0" font-family="Inter,system-ui,sans-serif" font-size="16" text-anchor="middle">Timeline unavailable</text>
</svg>
`)} `;

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
  const [graphLoadFailed, setGraphLoadFailed] = useState(false);
  const graphUrl = graphSrc;
  const fallbackGraphUrl = graphLoadFailed ? PLACEHOLDER_SVG_DATA_URI : graphUrl;

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
              src={fallbackGraphUrl}
              alt="timeline hero"
              className="timeline-hero-image"
              loading="lazy"
              decoding="async"
              onError={() => { setGraphLoadFailed(true); }}
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
                src={graphLoadFailed ? PLACEHOLDER_SVG_DATA_URI : graphUrl}
                alt="timeline large"
                style={{ width: '100%', height: '100%', minHeight: 260, objectFit: 'contain' }}
                loading="lazy"
                decoding="async"
                onError={() => { setGraphLoadFailed(true); }}
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
