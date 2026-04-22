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
  const [selected, setSelected] = useState<TimelineTask | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);
  useEffect(() => {
    (async () => {
      try {
        const storeMod = await import('@/state/appStore') as any;
        const start = storeMod.useAppStore.getState().startTimelineStream;
        start && start();
      } catch (e) {
        // ignore initialization failures during client hydration
      }
    })();
    return () => {
      (async () => {
        try {
          const storeMod = await import('@/state/appStore') as any;
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
    (t: TimelineTask) => {
      setSelected(t);
      selectTimelineTask(t);
    },
    [selectTimelineTask]
  );

  const progressForTask = (t: TimelineTask) => {
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

  const taskCards = useMemo(
    () => tasks.map((t: TimelineTask) => {
      const depth = depths.get(t.task_id) ?? 0;
      const indent = depth * 12;
      return (
        <button
          key={t.task_id}
          onClick={() => onSelectTask(t)}
          className={`timeline-hero-task ${selected?.task_id === t.task_id ? 'timeline-hero-task--active' : ''}`}
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
    [tasks, depths, selected, onSelectTask]
  );

  const expandedTaskButtons = useMemo(
    () => tasks.map((t: TimelineTask) => (
      <button
        key={t.task_id}
        onClick={() => { onSelectTask(t); setExpanded(false); }}
        className={`timeline-hero-summary-button ${selected?.task_id === t.task_id ? 'timeline-hero-summary-button--active' : ''}`}
      >
        <div>{t.title || 'Untitled task'}</div>
        <div>{(t.instructions || '').slice(0, 80)}</div>
      </button>
    )),
    [tasks, selected, onSelectTask]
  );

  return (
    <section className="timeline-hero shell-hero">
      <div className="timeline-hero__headline">
        <div>
          <p className="timeline-hero__label">Timeline overview</p>
          <h2 className="timeline-hero__title">Concierge task progression</h2>
          <p className="timeline-hero__subtitle">A clean, simple snapshot of the current task graph and next actions.</p>
        </div>
        <button className="timeline-hero__action" onClick={() => setExpanded(true)}>
          View full timeline
        </button>
      </div>

      <div className="timeline-hero__body">
        <div className="timeline-hero__graph">
          <img
            src={fallbackGraphUrl}
            alt="timeline hero"
            className="timeline-hero__graph-image"
            loading="lazy"
            decoding="async"
            onError={() => { setGraphLoadFailed(true); }}
          />
        </div>

        <div className="timeline-hero__tasks">
          {tasks.length === 0 ? (
            <div className="timeline-hero__empty">No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.</div>
          ) : (
            <div className="timeline-hero__task-grid">{taskCards}</div>
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
