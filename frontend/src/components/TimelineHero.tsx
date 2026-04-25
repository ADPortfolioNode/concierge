import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAppStore } from '@/state/appStore';
import { makeApiUrl } from '@/config/activeServer';

const PLACEHOLDER_SVG_DATA_URI = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111827" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <linearGradient id="line" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#60a5fa" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>
  </defs>
  <rect width="320" height="180" rx="20" fill="url(#bg)" />
  <rect x="18" y="44" width="44" height="84" rx="12" fill="rgba(96,165,250,0.18)" />
  <rect x="88" y="26" width="44" height="102" rx="12" fill="rgba(56,189,248,0.18)" />
  <rect x="158" y="58" width="44" height="72" rx="12" fill="rgba(168,85,247,0.18)" />
  <rect x="228" y="34" width="44" height="94" rx="12" fill="rgba(168,85,247,0.14)" />
  <path d="M24 152 Q88 96 160 126 T300 72" fill="none" stroke="url(#line)" stroke-width="8" stroke-linecap="round" opacity="0.95" />
  <circle cx="46" cy="118" r="6" fill="#bfdbfe" opacity="0.95" />
  <circle cx="126" cy="84" r="6" fill="#7dd3fc" opacity="0.95" />
  <circle cx="196" cy="110" r="6" fill="#c084fc" opacity="0.95" />
  <circle cx="276" cy="80" r="6" fill="#38bdf8" opacity="0.95" />
  <text x="160" y="165" fill="#e2e8f0" font-family="Inter,system-ui,sans-serif" font-size="15" text-anchor="middle">Timeline unavailable</text>
</svg>
`)} `;

type TimelineTask = {
  task_id: string;
  title?: string;
  instructions?: string;
  summary?: string;
  status?: string;
  depends_on?: string[];
  progress?: number;
  percent?: number;
};

const computeTaskDepths = (tasks: TimelineTask[]) => {
  const taskMap = new Map(tasks.map((task) => [task.task_id, task]));
  const depths = new Map<string, number>();

  const resolveDepth = (taskId: string, seen = new Set<string>()): number => {
    if (depths.has(taskId)) return depths.get(taskId)!;
    if (seen.has(taskId)) return 0;
    seen.add(taskId);

    const task = taskMap.get(taskId);
    if (!task || !Array.isArray(task.depends_on) || task.depends_on.length === 0) {
      depths.set(taskId, 0);
      return 0;
    }

    const depth = Math.max(
      0,
      ...task.depends_on.map((dep) => resolveDepth(dep, new Set(seen)))
    ) + 1;
    depths.set(taskId, depth);
    return depth;
  };

  tasks.forEach((task) => resolveDepth(task.task_id));
  return depths;
};

const TimelineHero: React.FC = () => {
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const fetchTimeline = useAppStore((s) => s.fetchTimeline);
  const selectTimelineTask = useAppStore((s) => s.selectTimelineTask);
  const selectedTaskMeta = useAppStore((s) => s.selectedTaskMeta);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);
  useEffect(() => {
    (async () => {
      try {
        const storeMod = await import('@/state/appStore') as Promise<{ useAppStore: typeof useAppStore }>;
        const start = storeMod.useAppStore.getState().startTimelineStream;
        start && start();
      } catch (e) {
        // ignore initialization failures during client hydration
      }
    })();
    return () => {
      (async () => {
        try {
          const storeMod = await import('@/state/appStore') as Promise<{ useAppStore: typeof useAppStore }>;
          const stop = storeMod.useAppStore.getState().stopTimelineStream;
          stop && stop();
        } catch (e) {
          // ignore cleanup failures
        }
      })();
    };
  }, []);

  const tasks = useMemo(() => {
    if (Array.isArray(timelinePlan?.tasks)) return timelinePlan.tasks;
    if (Array.isArray(timelinePlan?.plan?.tasks)) return timelinePlan.plan.tasks;
    return [] as TimelineTask[];
  }, [timelinePlan]);

  const depths = useMemo(() => computeTaskDepths(tasks), [tasks]);

  const vParam = useMemo(
    () => encodeURIComponent((timelinePlan && (timelinePlan.updated_at || '')) || String(Date.now())),
    [timelinePlan]
  );
  const graphPath = useMemo(() => `/api/v1/concierge/timeline/graph?v=${vParam}`, [vParam]);
  const graphSrc = useMemo(() => makeApiUrl(graphPath), [graphPath]);
  const [graphLoadFailed, setGraphLoadFailed] = useState(false);
  const graphUrl = graphSrc;
  const fallbackGraphUrl = useMemo(
    () => (graphLoadFailed ? PLACEHOLDER_SVG_DATA_URI : graphUrl),
    [graphLoadFailed, graphUrl]
  );

  const onSelectTask = useCallback(
    (t: TimelineTask | null) => {
      selectTimelineTask(t);
    },
    [selectTimelineTask]
  );

  const progressForTask = (t: TimelineTask | null) => {
    if (!t) return 0;
    const progressValue = typeof t.progress === 'number'
      ? t.progress
      : typeof t.percent === 'number'
      ? t.percent
      : t.status === 'completed' || t.status === 'success'
      ? 100
      : t.status === 'running' || t.status === 'started'
      ? 46
      : t.status === 'queued' || t.status === 'pending'
      ? 18
      : 12;
    return Math.min(100, Math.max(0, progressValue));
  };

  const branchNodes = useMemo(() => {
    const source = tasks.length > 0
      ? tasks.slice(0, Math.min(tasks.length, 6))
      : [
          { task_id: 'assistant-start', title: 'Assistant starts', status: 'started' },
          { task_id: 'strategy-branch', title: 'Strategy branch', status: 'running' },
          { task_id: 'plan-tasks', title: 'Plan tasks', status: 'queued' },
          { task_id: 'execute-actions', title: 'Execute actions', status: 'pending' },
          { task_id: 'review-output', title: 'Review results', status: 'pending' },
        ];

    const total = Math.max(source.length, 1);
    return source.map((task, idx) => {
      const depth = depths.get(task.task_id) ?? (idx === 0 ? 0 : 1);
      const x = 72 + (idx * (576 / Math.max(total - 1, 1)));
      const baseY = 160;
      const offset = depth === 0 ? 0 : (idx % 2 === 0 ? -1 : 1) * (32 + depth * 12);
      return {
        ...task,
        x,
        y: baseY + offset,
        color: ['#38bdf8', '#7c3aed', '#f97316', '#22c55e', '#ec4899'][idx % 5],
      };
    });
  }, [tasks, depths]);

  const branchMainPath = useMemo(() => {
    if (branchNodes.length === 0) return '';
    const startX = branchNodes[0].x;
    const endX = branchNodes[branchNodes.length - 1].x;
    return `M ${startX} 160 C ${startX + 72} 160, ${endX - 72} 160, ${endX} 160`;
  }, [branchNodes]);

  const taskCards = useMemo(
    () => tasks.map((t: TimelineTask) => {
      const depth = depths.get(t.task_id) ?? 0;
      const indent = depth * 12;
      return (
        <button
          key={t.task_id}
          onClick={() => onSelectTask(t)}
          className={`timeline-hero-task ${selectedTaskMeta?.task_id === t.task_id ? 'timeline-hero-task--active' : ''}`}
          style={{ marginLeft: indent }}
        >
          <div className="timeline-hero-task-title">{t.title || 'Untitled task'}</div>
          <div className="timeline-hero-task-details">{(t.instructions || t.summary || '').slice(0, 72)}</div>
          <div className="timeline-hero-task-progress-bar">
            <div style={{ width: `${progressForTask(t)}%` }} />
          </div>
        </button>
      );
    }),
    [tasks, depths, selectedTaskMeta, onSelectTask]
  );

  const expandedTaskButtons = useMemo(
    () => tasks.map((t: TimelineTask) => (
      <button
        key={t.task_id}
        onClick={() => { onSelectTask(t); setExpanded(false); }}
        className={`timeline-hero-summary-button ${selectedTaskMeta?.task_id === t.task_id ? 'timeline-hero-summary-button--active' : ''}`}
      >
        <div>{t.title || 'Untitled task'}</div>
        <div>{(t.instructions || '').slice(0, 80)}</div>
      </button>
    )),
    [tasks, selectedTaskMeta, onSelectTask]
  );

  return (
    <section className="timeline-hero shell-hero">
      <div className="timeline-hero__headline">
        <div>
          <p className="timeline-hero__label">Assistant timeline</p>
          <h2 className="timeline-hero__title">Assistant branch timeline</h2>
          <p className="timeline-hero__subtitle">Visualize the assistant's strategy as a branching timeline with tasks and progress.</p>
        </div>
        <button className="timeline-hero__action" onClick={() => setExpanded(true)}>
          View full timeline
        </button>
      </div>

      <div className="timeline-hero__body">
        <div className="timeline-hero__graph timeline-hero__branch-graph">
          <svg viewBox="0 0 720 260" className="timeline-hero__branch-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Assistant branch timeline">
            <defs>
              <linearGradient id="branchGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#60a5fa" />
                <stop offset="50%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#38bdf8" />
              </linearGradient>
            </defs>
            <path className="timeline-branch-main-line" d={branchMainPath} />
            {branchNodes.map((node) => (
              <path
                key={`edge-${node.task_id}`}
                className="timeline-branch-edge"
                d={`M ${node.x} ${node.y} L ${node.x} 160`}
              />
            ))}
            {branchNodes.map((node, idx) => (
              <g key={`node-${node.task_id}`} className="timeline-branch-node-group" style={{ animationDelay: `${idx * 0.15}s` }}>
                <circle className="timeline-branch-node-ring" cx={node.x} cy={node.y} r="24" />
                <circle className="timeline-branch-node" cx={node.x} cy={node.y} r="12" fill={node.color} />
                <text
                  className="timeline-branch-label"
                  x={node.x}
                  y={node.y < 160 ? node.y - 20 : node.y + 28}
                  textAnchor="middle"
                >
                  {node.title?.slice(0, 18)}
                </text>
              </g>
            ))}
          </svg>
        </div>

        <div className="timeline-hero__tasks">
          {tasks.length === 0 ? (
            <div className="timeline-hero__empty">No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.</div>
          ) : (
            <div className="timeline-hero__task-grid">{taskCards}</div>
          )}
          {selectedTaskMeta && (
            <div style={{ marginTop: 18, padding: 16, background: 'rgba(15, 23, 42, 0.95)', borderRadius: 16, border: '1px solid rgba(148, 163, 184, 0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>{selectedTaskMeta.title || selectedTaskMeta.task_id}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>{selectedTaskMeta.status ? `Status: ${selectedTaskMeta.status}` : 'Status: unknown'}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onSelectTask(null)}
                  style={{ background: 'transparent', border: '1px solid rgba(148, 163, 184, 0.25)', borderRadius: 8, color: '#cbd5e1', padding: '6px 10px', cursor: 'pointer' }}
                >
                  Hide details
                </button>
              </div>
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ flex: 1, background: 'rgba(148, 163, 184, 0.12)', borderRadius: 999, height: 10, overflow: 'hidden' }}>
                  <div style={{ width: `${progressForTask(selectedTaskMeta)}%`, height: 10, borderRadius: 999, background: '#22c55e' }} />
                </div>
                <div style={{ minWidth: 44, fontSize: 12, color: '#e2e8f0' }}>{progressForTask(selectedTaskMeta)}%</div>
              </div>
              {(selectedTaskMeta.summary || selectedTaskMeta.instructions) && (
                <div style={{ marginTop: 12, fontSize: 13, lineHeight: 1.6, color: '#cbd5e1' }}>
                  {selectedTaskMeta.summary || selectedTaskMeta.instructions}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="timeline-hero__modal-backdrop" onClick={() => setExpanded(false)}>
          <div className="timeline-hero__modal" onClick={(e) => e.stopPropagation()}>
            <div className="timeline-hero__modal-header">
              <h3>Fullscreen timeline</h3>
              <button onClick={() => setExpanded(false)}>Close</button>
            </div>
            <img
              src={graphLoadFailed ? PLACEHOLDER_SVG_DATA_URI : graphUrl}
              alt="timeline large"
              className="timeline-hero__modal-image"
              loading="lazy"
              decoding="async"
              onError={() => { setGraphLoadFailed(true); }}
            />
            <div className="timeline-hero__modal-tasks">{expandedTaskButtons}</div>
          </div>
        </div>
      )}
    </section>
  );
};

export default TimelineHero;
