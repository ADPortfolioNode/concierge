import React, { useMemo, useState } from 'react';
import type { TaskTree, TaskTreeNode } from '@/api/taskService';
import AssistantRiver from '@/components/river/AssistantRiver';

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

function flattenNodes(node: TaskTreeNode, depth = 0): Array<{ node: TaskTreeNode; depth: number }> {
  const rows: Array<{ node: TaskTreeNode; depth: number }> = [{ node, depth }];
  node.children?.forEach((child) => rows.push(...flattenNodes(child, depth + 1)));
  return rows;
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

const TaskNodeRow: React.FC<{ node: TaskTreeNode; depth: number }> = ({ node, depth }) => {
  const color = resolveStatusColor(node.status || node.state, node.color);
  const label = node.status || node.state || 'unknown';
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        background: '#F8FAFF',
        border: '1px solid #DBEAFE',
        borderRadius: 7,
        padding: '8px 14px',
        fontSize: 13,
        marginLeft: depth * 18,
      }}
    >
      <span
        style={{
          fontFamily: 'monospace',
          fontSize: 11,
          color: '#2563EB',
          flex: 1,
          minWidth: 0,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
        title={node.task_name || node.task_id}
      >
        {node.task_name || node.task_id}
      </span>
      <span
        style={{
          padding: '2px 8px',
          borderRadius: 99,
          background: `${color}22`,
          color,
          fontSize: 11,
          fontWeight: 600,
          textTransform: 'uppercase',
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      <span style={{ fontSize: 11, color: '#64748B', minWidth: 36, textAlign: 'right', flexShrink: 0 }}>
        {typeof node.progress === 'number' ? `${node.progress}%` : '—'}
      </span>
      <span
        style={{
          fontFamily: 'monospace',
          fontSize: 10,
          color: '#94A3B8',
          flexShrink: 0,
        }}
      >
        {node.task_id.slice(0, 12)}…
      </span>
    </div>
  );
};

interface TaskStatusViewProps {
  tree: TaskTree;
  loading?: boolean;
  error?: string | null;
  lastUpdated?: Date | null;
}

const TaskStatusView: React.FC<TaskStatusViewProps> = ({ tree, loading, error, lastUpdated }) => {
  const [selectedNode, setSelectedNode] = useState<TaskTreeNode | null>(null);
  const rows = useMemo(() => flattenNodes(tree), [tree]);
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header card */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1px solid #DBEAFE',
          borderRadius: 14,
          padding: '20px 22px',
          boxShadow: '0 4px 16px rgba(37,99,235,0.08)',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94A3B8', marginBottom: 6 }}>
              Task status
            </div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0F172A', lineHeight: 1.3 }}>
              {tree.task_name || 'Untitled task'}
            </h2>
            {goal ? (
              <p style={{ margin: '10px 0 0', fontSize: 14, color: '#475569', lineHeight: 1.65 }}>{goal}</p>
            ) : null}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <span
              style={{
                padding: '4px 12px',
                borderRadius: 99,
                background: `${color}22`,
                color,
                fontSize: 12,
                fontWeight: 700,
                textTransform: 'uppercase',
              }}
            >
              {tree.status || tree.state || 'unknown'}
            </span>
            {lastUpdated ? (
              <span style={{ fontSize: 11, color: '#94A3B8' }}>Updated {lastUpdated.toLocaleTimeString()}</span>
            ) : null}
            {loading ? <span style={{ fontSize: 11, color: '#2563EB' }}>Refreshing…</span> : null}
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#64748B', marginBottom: 6 }}>
            <span>Progress</span>
            <span>{typeof tree.progress === 'number' ? `${tree.progress}%` : '—'}</span>
          </div>
          <div style={{ height: 8, width: '100%', background: '#DBEAFE', borderRadius: 999 }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, tree.progress ?? 0))}%`,
                height: 8,
                borderRadius: 999,
                background: color,
                transition: 'width 0.3s ease',
              }}
            />
          </div>
        </div>

        <div
          style={{
            marginTop: 14,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 16,
            fontSize: 12,
            color: '#64748B',
          }}
        >
          <span>
            Task ID:{' '}
            <code style={{ fontFamily: 'monospace', color: '#2563EB', background: '#EFF6FF', padding: '2px 6px', borderRadius: 4 }}>
              {tree.task_id}
            </code>
          </span>
          {startTime ? <span>Started {startTime}</span> : null}
          {typeof completedSteps === 'number' && typeof totalSteps === 'number' ? (
            <span>{completedSteps} of {totalSteps} steps complete</span>
          ) : null}
          <span>{terminal ? 'Polling stopped' : 'Live polling'}</span>
        </div>

        {error ? (
          <div
            style={{
              marginTop: 14,
              fontSize: 13,
              color: '#B91C1C',
              background: 'rgba(220,38,38,0.06)',
              border: '1px solid rgba(220,38,38,0.2)',
              borderRadius: 8,
              padding: '10px 14px',
            }}
          >
            {error}
          </div>
        ) : null}

        {resultSummary ? (
          <div style={{ marginTop: 16, padding: 14, background: '#F0FDF4', border: '1px solid rgba(5,150,105,0.2)', borderRadius: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#059669', marginBottom: 6 }}>
              Result summary
            </div>
            <p style={{ margin: 0, fontSize: 14, color: '#065F46', lineHeight: 1.65 }}>{resultSummary}</p>
          </div>
        ) : null}
      </div>

      {/* River visualization when branches exist */}
      {tree.children?.length > 0 ? (
        <AssistantRiver tree={tree} selectedNode={selectedNode} onSelectNode={setSelectedNode} />
      ) : null}

      {/* Flat task tree */}
      <div>
        <h3
          style={{
            fontSize: 13,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: '#94A3B8',
            margin: '0 0 10px',
            paddingBottom: 8,
            borderBottom: '1px solid #DBEAFE',
          }}
        >
          Task tree ({rows.length} node{rows.length !== 1 ? 's' : ''})
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {rows.map(({ node, depth }) => (
            <TaskNodeRow key={node.task_id} node={node} depth={depth} />
          ))}
        </div>
      </div>

      {/* Execution logs */}
      {Array.isArray(logs) && logs.length > 0 ? (
        <div>
          <h3
            style={{
              fontSize: 13,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#94A3B8',
              margin: '0 0 10px',
              paddingBottom: 8,
              borderBottom: '1px solid #DBEAFE',
            }}
          >
            Execution log
          </h3>
          <pre
            style={{
              fontSize: 11,
              color: '#334155',
              background: '#F8FAFF',
              border: '1px solid #DBEAFE',
              borderRadius: 8,
              padding: '12px 14px',
              overflowX: 'auto',
              maxHeight: 240,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              margin: 0,
            }}
          >
            {JSON.stringify(logs, null, 2)}
          </pre>
        </div>
      ) : null}

      {/* Raw metadata (collapsed) */}
      {tree.metadata && Object.keys(tree.metadata).length > 0 ? (
        <details style={{ background: '#F8FAFF', border: '1px solid #DBEAFE', borderRadius: 10, padding: '12px 16px' }}>
          <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#475569' }}>Raw metadata</summary>
          <pre
            style={{
              marginTop: 12,
              fontSize: 11,
              color: '#334155',
              overflowX: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {JSON.stringify(tree.metadata, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
};

export default TaskStatusView;