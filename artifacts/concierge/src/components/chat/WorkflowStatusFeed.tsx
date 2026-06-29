import React from 'react';
import { Link } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';
import { workflowProgress } from '@/utils/workflowStatus';

const kindStyle: Record<string, { bg: string; border: string; color: string; icon: string }> = {
  started: { bg: '#EFF6FF', border: '#BFDBFE', color: '#1E40AF', icon: '▶' },
  progress: { bg: '#F8FAFF', border: '#DBEAFE', color: '#475569', icon: '◔' },
  completed: { bg: '#F0FDF4', border: 'rgba(5,150,105,0.25)', color: '#065F46', icon: '✓' },
  failed: { bg: '#FEF2F2', border: '#FECACA', color: '#991B1B', icon: '✕' },
  workflow_complete: { bg: '#F0FDF4', border: 'rgba(5,150,105,0.3)', color: '#047857', icon: '★' },
  workflow_failed: { bg: '#FEF2F2', border: '#FECACA', color: '#991B1B', icon: '!' },
};

const WorkflowStatusFeed: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const taskTree = useAppStore((s) => s.taskTree);
  const updates = useAppStore((s) => s.workflowUpdates);

  if (!taskThreadId || updates.length === 0) return null;

  const { completed, total, percent } = workflowProgress(taskTree);
  const goal =
    (taskTree?.metadata as { metadata?: { goal?: string }; goal?: string } | undefined)?.metadata?.goal ??
    (taskTree?.metadata as { goal?: string } | undefined)?.goal ??
    taskTree?.task_name;

  return (
    <div
      style={{
        borderBottom: '1px solid #DBEAFE',
        background: 'linear-gradient(180deg, #F8FAFF 0%, #FFFFFF 100%)',
        padding: '10px 12px 8px',
        flexShrink: 0,
        maxHeight: 220,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#2563EB' }}>
            Workflow progress
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#0F172A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {goal || 'Active orchestration'}
          </div>
        </div>
        <Link
          to={`/tasks/${encodeURIComponent(taskThreadId)}`}
          style={{ fontSize: 11, color: '#2563EB', fontWeight: 600, textDecoration: 'none', flexShrink: 0 }}
        >
          Details →
        </Link>
      </div>

      {total > 0 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748B', marginBottom: 4 }}>
            <span>{completed} of {total} steps complete</span>
            <span>{percent}%</span>
          </div>
          <div style={{ height: 5, background: '#DBEAFE', borderRadius: 99, overflow: 'hidden' }}>
            <div
              style={{
                width: `${percent}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #2563EB, #22C55E)',
                transition: 'width 0.35s ease',
              }}
            />
          </div>
        </div>
      )}

      <div
        style={{
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 5,
          paddingRight: 2,
        }}
      >
        {updates.slice(-8).reverse().map((u) => {
          const style = kindStyle[u.kind] ?? kindStyle.progress;
          return (
            <div
              key={u.id}
              style={{
                fontSize: 11,
                lineHeight: 1.45,
                padding: '6px 8px',
                borderRadius: 8,
                background: style.bg,
                border: `1px solid ${style.border}`,
                color: style.color,
              }}
            >
              <span style={{ marginRight: 6 }}>{style.icon}</span>
              <strong>{u.stepName}</strong>
              {u.kind === 'progress' ? ` — ${u.progress}%` : null}
              {u.kind === 'completed' && u.summary ? (
                <div style={{ marginTop: 4, opacity: 0.9, fontWeight: 400, wordBreak: 'break-word' }}>
                  {u.summary.length > 120 ? `${u.summary.slice(0, 119)}…` : u.summary}
                </div>
              ) : null}
              {u.kind === 'failed' && u.summary ? (
                <div style={{ marginTop: 4, fontWeight: 400, wordBreak: 'break-word' }}>{u.summary}</div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowStatusFeed;