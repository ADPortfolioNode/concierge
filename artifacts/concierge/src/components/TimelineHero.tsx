import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAppStore } from '@/state/appStore';
import { makeApiUrl } from '@/config/activeServer';
import ThreadVisualizer from '@/components/ThreadVisualizer';

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

// ── Idle placeholder shown when no thread is active and no tasks exist ───────
const TimelineHeroIdle: React.FC = () => (
  <section className="timeline-hero shell-hero" style={{ minHeight: 'auto' }}>
    <div className="timeline-hero__headline" style={{ paddingBottom: 0 }}>
      <div>
        <p className="timeline-hero__label">Assistant timeline</p>
        <h2 className="timeline-hero__title">No active thread</h2>
        <p className="timeline-hero__subtitle" style={{ maxWidth: 480 }}>
          Concierge is ready. Start by asking it to create a plan, set a goal, or run a background task — the live thread graph will appear here.
        </p>
      </div>
    </div>
  </section>
);

const TimelineHero: React.FC = () => {
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const fetchTimeline = useAppStore((s) => s.fetchTimeline);
  const selectTimelineTask = useAppStore((s) => s.selectTimelineTask);
  const selectedTaskMeta = useAppStore((s) => s.selectedTaskMeta);
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const [expanded, setExpanded] = useState(false);
  const [viewMode, setViewMode] = useState<'linear' | 'visual' | 'split'>(taskThreadId ? 'visual' : 'linear');

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  useEffect(() => {
    (async () => {
      try {
        const storeMod = await import('@/state/appStore') as unknown as { useAppStore: typeof useAppStore };
        const start = storeMod.useAppStore.getState().startTimelineStream;
        start && start();
      } catch (e) {
        // ignore initialization failures during client hydration
      }
    })();
    return () => {
      (async () => {
        try {
          const storeMod = await import('@/state/appStore') as unknown as { useAppStore: typeof useAppStore };
          const stop = storeMod.useAppStore.getState().stopTimelineStream;
          stop && stop();
        } catch (e) {
          // ignore cleanup failures
        }
      })();
    };
  }, []);

  useEffect(() => {
    if (taskThreadId && viewMode === 'linear') {
      setViewMode('visual');
    }
  }, [taskThreadId, viewMode]);

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
      ? tasks
      : [
          { task_id: 'assistant-start', title: 'Assistant starts', status: 'started' },
          { task_id: 'strategy-branch', title: 'Strategy branch', status: 'running' },
          { task_id: 'plan-tasks', title: 'Plan tasks', status: 'queued' },
          { task_id: 'execute-actions', title: 'Execute actions', status: 'pending' },
          { task_id: 'review-output', title: 'Review results', status: 'pending' },
        ];

    const byDepth = new Map<number, TimelineTask[]>();
    source.forEach((task: TimelineTask) => {
      const d = depths.get(task.task_id) ?? 0;
      if (!byDepth.has(d)) byDepth.set(d, []);
      byDepth.get(d)!.push(task);
    });

    return source.map((task: TimelineTask, idx: number) => {
      const depth = depths.get(task.task_id) ?? 0;
      const peers = byDepth.get(depth) ?? [task];
      const peerIndex = peers.findIndex((t) => t.task_id === task.task_id);
      const x = 120 + depth * 148;
      const y = 110 + (peerIndex - (peers.length - 1) / 2) * 56;
      return {
        ...task,
        x,
        y,
        depth,
        color: ['#38bdf8', '#7c3aed', '#f97316', '#22c55e', '#ec4899', '#8b5cf6', '#06b6d4'][idx % 7],
      };
    });
  }, [tasks, depths]);

  const branchMainPath = useMemo(() => {
    if (branchNodes.length === 0) return '';
    const endX = Math.max(...branchNodes.map((n: { x: number }) => n.x));
    return `M 46 110 L ${endX - 12} 110`;
  }, [branchNodes]);

  const taskCards = useMemo(
    () => tasks.map((t: TimelineTask) => {
      const depth = depths.get(t.task_id) ?? 0;
      const indent = depth * 12;
      const isActive = selectedTaskMeta?.task_id === t.task_id;
      return (
        <button
          key={t.task_id}
          onClick={() => onSelectTask(isActive ? null : t)}
          className={`timeline-hero-task ${isActive ? 'timeline-hero-task--active' : 'timeline-hero-task--collapsed'}`}
          style={{ marginLeft: indent }}
          aria-expanded={isActive}
        >
          <div className="timeline-hero-task-headline-row">
            <div className="timeline-hero-task-title">{t.title || 'Untitled task'}</div>
            <div className="timeline-hero-task-summary-label">{t.status ? t.status.toUpperCase() : 'PENDING'}</div>
          </div>
          {isActive ? (
            <>
              <div className="timeline-hero-task-details">{(t.instructions || t.summary || '').slice(0, 220)}</div>
              <div className="timeline-hero-task-progress-bar">
                <div style={{ width: `${progressForTask(t)}%` }} />
              </div>
            </>
          ) : (
            <div className="timeline-hero-task-teaser">{progressForTask(t)}% · tap to expand</div>
          )}
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

  if (!taskThreadId && tasks.length === 0) {
    return <TimelineHeroIdle />;
  }

  return (
    <section className="timeline-hero shell-hero">
      <div className="timeline-hero__headline">
        <div>
          <p className="timeline-hero__label">Assistant timeline</p>
          <h2 className="timeline-hero__title">Agentic thread visualizer</h2>
          <p className="timeline-hero__subtitle">Watch Concierge execute the thread as live nodes, tool calls, and retrievals in a dynamic graph view.</p>
        </div>
        <div className="timeline-hero__view-toggle">
          <button
            type="button"
            className={viewMode === 'linear' ? 'timeline-view-toggle--active' : ''}
            onClick={() => setViewMode('linear')}
          >
            Chat
          </button>
          <button
            type="button"
            className={viewMode === 'visual' ? 'timeline-view-toggle--active' : ''}
            onClick={() => setViewMode('visual')}
          >
            Visualizer
          </button>
          <button
            type="button"
            className={viewMode === 'split' ? 'timeline-view-toggle--active' : ''}
            onClick={() => setViewMode('split')}
          >
            Split
          </button>
        </div>
      </div>

      <div className="timeline-hero__body">
        {viewMode === 'visual' || viewMode === 'split' ? (
          <div className="timeline-hero__graph timeline-hero__visualizer-graph">
            <ThreadVisualizer />
          </div>
        ) : (
          <div className="timeline-hero__graph timeline-hero__branch-graph" data-testid="timeline-horizontal-tree">
            <svg viewBox="0 0 720 220" className="timeline-hero__branch-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Assistant horizontal task tree">
              <defs>
                <linearGradient id="branchGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="50%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#38bdf8" />
                </linearGradient>
              </defs>
              {/* root anchor — tree grows left → right */}
              <circle cx="36" cy="110" r="10" fill="#2563EB" opacity="0.9" />
              <text x="36" y="88" textAnchor="middle" className="timeline-branch-label">Start</text>
              <path className="timeline-branch-main-line" d={branchMainPath.replace(/^M (\d+)/, 'M 46')} />
              {branchNodes.map((node: any, idx: number) => {
                const prevX = idx === 0 ? 46 : branchNodes[idx - 1].x + 12;
                const midY = 110;
                return (
                  <path
                    key={`edge-${node.task_id}`}
                    className="timeline-branch-edge"
                    d={`M ${prevX} ${midY} C ${(prevX + node.x) / 2} ${midY}, ${(prevX + node.x) / 2} ${node.y}, ${node.x - 12} ${node.y}`}
                  />
                );
              })}
              {branchNodes.map((node: any, idx: number) => (
                <g key={`node-${node.task_id}`} className="timeline-branch-node-group" style={{ animationDelay: `${idx * 0.15}s` }}>
                  <rect
                    x={node.x - 52}
                    y={node.y - 22}
                    width="104"
                    height="44"
                    rx="10"
                    fill="#FFFFFF"
                    stroke={node.color}
                    strokeWidth="2"
                  />
                  <circle className="timeline-branch-node" cx={node.x} cy={node.y} r="6" fill={node.color} />
                  <text className="timeline-branch-label" x={node.x} y={node.y + 4} textAnchor="middle">
                    {node.title?.slice(0, 14)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        )}

        <div className="timeline-hero__tasks">
          {tasks.length === 0 ? (
            <div className="timeline-hero__empty">No timeline tasks are available yet. Ask Concierge to create a plan or add a goal.</div>
          ) : (
            <div className="timeline-hero__task-grid">{taskCards}</div>
          )}

        </div>
      </div>
    </section>
  );
};

export default TimelineHero;
