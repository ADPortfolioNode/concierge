import React, { useMemo, useState } from 'react';
import type { TaskTree, TaskTreeNode } from '@/api/taskService';
import AssistantRiver from '@/components/river/AssistantRiver';
import AccordionBadge from '@/components/tasks/AccordionBadge';
import ResultSummaryBlock from '@/components/tasks/ResultSummaryBlock';
import { pollingStatusLabel, resolveTaskTitle } from '@/components/tasks/taskDisplayUtils';
import { stepDisplayName } from '@/utils/workflowStatus';

const statusColor: Record<string, string> = {
  queued: '#6b7280',
  running: '#0891b2',
  PROGRESS: '#0891b2',
  STARTED: '#0891b2',
  PENDING: '#6b7280',
  pending: '#6b7280',
  completed: '#059669',
  done: '#059669',
  SUCCESS: '#059669',
  failed: '#dc2626',
  error: '#dc2626',
  FAILURE: '#dc2626',
  unavailable: '#6b7280',
  KILLED: '#dc2626',
};

function resolveStatusColor(status?: string, fallback?: string) {
  if (!status) return fallback ?? '#6b7280';
  return statusColor[status] ?? fallback ?? '#6b7280';
}

function isTerminal(status?: string, progress?: number) {
  if (!status) return false;
  const s = status.toLowerCase();
  return ['done', 'completed', 'success', 'failed', 'error', 'failure', 'killed'].includes(s) || progress === 100;
}

function formatTimestamp(value: unknown) {
  if (typeof value !== 'number') return null;
  const ms = value > 1e12 ? value : value * 1000;
  try {
    return new Date(ms).toLocaleString();
  } catch {
    return null;
  }
}

type OpenSection = 'result' | 'logs' | 'meta' | null;

interface TaskStatusViewProps {
  tree: TaskTree;
  loading?: boolean;
  error?: string | null;
  lastUpdated?: Date | null;
}

const TaskStatusView: React.FC<TaskStatusViewProps> = ({ tree, loading, error, lastUpdated }) => {
  const [selectedNode, setSelectedNode] = useState<TaskTreeNode | null>(null);
  const [openSection, setOpenSection] = useState<OpenSection>(null);
  const hasBranches = (tree.children?.length ?? 0) > 0;
  const color = resolveStatusColor(tree.status || tree.state, tree.color);
  const meta = tree.metadata as {
    metadata?: { goal?: string };
    goal?: string;
    completed_steps?: number;
    total_steps?: number;
  } | undefined;
  const goal = meta?.metadata?.goal ?? meta?.goal;
  const completedSteps = meta?.completed_steps;
  const totalSteps = meta?.total_steps;
  const resultSummary = (tree.metadata as { result_summary?: string } | undefined)?.result_summary;
  const logs = (tree.metadata as { logs?: unknown[] } | undefined)?.logs;
  const startTime = formatTimestamp((tree.metadata as { start_time?: number } | undefined)?.start_time);
  const terminal = isTerminal(tree.status || tree.state, tree.progress);
  const displayTitle = resolveTaskTitle(tree.task_name, goal);
  const pollLabel = pollingStatusLabel(terminal, !!loading);
  const stepCount = tree.children?.length ?? totalSteps ?? 0;

  const toggleSection = (section: OpenSection) => {
    setOpenSection((prev) => (prev === section ? null : section));
  };

  const accordionBadges = useMemo(() => {
    const items: Array<{ key: OpenSection; label: string; hint: string; tone: 'default' | 'success' | 'warn' | 'muted' }> = [];
    if (resultSummary) {
      items.push({ key: 'result', label: 'Result', hint: 'Summary', tone: 'success' });
    }
    if (Array.isArray(logs) && logs.length > 0) {
      items.push({ key: 'logs', label: 'Logs', hint: String(logs.length), tone: 'muted' });
    }
    if (import.meta.env.DEV && tree.metadata && Object.keys(tree.metadata).length > 0) {
      items.push({ key: 'meta', label: 'Debug', hint: 'Dev', tone: 'muted' });
    }
    return items;
  }, [logs, resultSummary, tree.metadata]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="task-status-card">
        <div className="task-status-card__header">
          <div className="task-status-card__title-block">
            <span className="task-status-card__eyebrow">Task</span>
            <h2 className="task-status-card__title">{displayTitle}</h2>
          </div>
          <span
            className="task-status-card__status-pill"
            style={{ background: `${color}22`, color }}
          >
            {tree.status || tree.state || 'unknown'}
          </span>
        </div>

        <div className="task-status-card__progress">
          <div className="task-status-card__progress-labels">
            <span>Progress</span>
            <span>{typeof tree.progress === 'number' ? `${tree.progress}%` : '—'}</span>
          </div>
          <div className="task-status-card__progress-track">
            <div
              className="task-status-card__progress-fill"
              style={{ width: `${Math.min(100, Math.max(0, tree.progress ?? 0))}%`, background: color }}
            />
          </div>
        </div>

        <div className="task-status-card__meta">
          {typeof completedSteps === 'number' && typeof totalSteps === 'number' ? (
            <span>{completedSteps}/{totalSteps} steps</span>
          ) : stepCount > 0 ? (
            <span>{stepCount} step{stepCount !== 1 ? 's' : ''}</span>
          ) : null}
          {startTime ? <span>Started {startTime}</span> : null}
          <span className={`task-status-card__live ${terminal ? 'task-status-card__live--done' : ''}`}>
            <span className="task-status-card__live-dot" />
            {pollLabel}
          </span>
          {lastUpdated ? <span className="task-status-card__updated">Updated {lastUpdated.toLocaleTimeString()}</span> : null}
        </div>

        {error ? <div className="task-status-card__error">{error}</div> : null}
      </div>

      {hasBranches ? (
        <AssistantRiver
          tree={tree}
          selectedNode={selectedNode}
          onSelectNode={setSelectedNode}
          displayTitle={displayTitle}
        />
      ) : (
        <div className="task-status-card task-status-card--compact">
          <div className="task-status-card__header">
            <span className="task-status-card__eyebrow">Step</span>
            <span className="task-status-card__status-pill" style={{ background: `${color}22`, color }}>
              {tree.status || tree.state || 'unknown'}
            </span>
          </div>
          <p className="task-status-card__single-step">{stepDisplayName(tree)}</p>
        </div>
      )}

      {accordionBadges.length > 0 ? (
        <div className="task-status-accordions">
          <div className="task-status-accordions__badges">
            {accordionBadges.map((item) => (
              <AccordionBadge
                key={item.key}
                id={item.key || 'section'}
                label={item.label}
                hint={item.hint}
                tone={item.tone}
                active={openSection === item.key}
                open={false}
                onToggle={() => toggleSection(item.key)}
              />
            ))}
          </div>
          {openSection === 'result' && resultSummary ? (
            <div className="accordion-badge__panel task-status-accordions__panel">
              <ResultSummaryBlock summary={resultSummary} embedded />
            </div>
          ) : null}
          {openSection === 'logs' && Array.isArray(logs) ? (
            <div className="accordion-badge__panel task-status-accordions__panel">
              <pre className="task-status-accordions__pre">{JSON.stringify(logs, null, 2)}</pre>
            </div>
          ) : null}
          {openSection === 'meta' ? (
            <div className="accordion-badge__panel task-status-accordions__panel">
              <pre className="task-status-accordions__pre">{JSON.stringify(tree.metadata, null, 2)}</pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

export default TaskStatusView;