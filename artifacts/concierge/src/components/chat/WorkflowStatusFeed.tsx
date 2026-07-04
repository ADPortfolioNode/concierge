import React from 'react';
import { Link } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';
import { workflowProgress } from '@/utils/workflowStatus';

const WorkflowStatusFeed: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const taskTree = useAppStore((s) => s.taskTree);
  const updates = useAppStore((s) => s.workflowUpdates);

  if (!taskThreadId || updates.length === 0) return null;

  const { completed, total, percent } = workflowProgress(taskTree);
  const latest = updates[updates.length - 1];
  const latestLabel =
    latest?.kind === 'workflow_complete'
      ? 'Complete'
      : latest?.kind === 'workflow_failed'
        ? 'Finished with errors'
        : latest?.stepName ?? 'Running';

  return (
    <div
      style={{
        borderBottom: '1px solid #DBEAFE',
        background: '#F0F8FF',
        padding: '8px 12px',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#0F172A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {latestLabel}
          {total > 0 ? ` · ${completed}/${total}` : ''}
        </span>
        <Link
          to={`/tasks/${encodeURIComponent(taskThreadId)}`}
          style={{ fontSize: 11, color: '#2563EB', fontWeight: 600, textDecoration: 'none', flexShrink: 0 }}
        >
          Tasks →
        </Link>
      </div>
      {total > 0 && (
        <div style={{ height: 4, background: '#DBEAFE', borderRadius: 99, overflow: 'hidden' }}>
          <div
            style={{
              width: `${percent}%`,
              height: '100%',
              background: '#2563EB',
              transition: 'width 0.35s ease',
            }}
          />
        </div>
      )}
    </div>
  );
};

export default WorkflowStatusFeed;