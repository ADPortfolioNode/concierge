import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchTaskTree, type TaskTree } from '@/api/taskService';
import TaskStatusView from '@/components/tasks/TaskStatusView';
import PageSection from '@/components/PageSection';
import ThreadVisualizer from '@/components/ThreadVisualizer';
import { useAppStore } from '@/state/appStore';

const POLL_MS = 2500;

function isStillRunning(tree: TaskTree) {
  const status = (tree.status || tree.state || '').toLowerCase();
  if (['done', 'completed', 'success', 'failed', 'error', 'failure', 'killed'].includes(status)) return false;
  if (tree.progress === 100) return false;
  return true;
}

const TaskStatusPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const applyTaskTreeUpdate = useAppStore((s) => s.applyTaskTreeUpdate);

  const [tree, setTree] = useState<TaskTree | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadStatus = useCallback(async (silent = false) => {
    if (!taskId) return null;
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const data = await fetchTaskTree(taskId);
      setTree(data);
      applyTaskTreeUpdate(data, taskId);
      setLastUpdated(new Date());
      return data;
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ??
        (err as { message?: string })?.message ??
        'Failed to load task status';
      setError(String(message));
      return null;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [applyTaskTreeUpdate, taskId]);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    const startPolling = async () => {
      const data = await loadStatus();
      if (cancelled || !data) return;
      if (!isStillRunning(data)) return;

      timer = setInterval(async () => {
        const fresh = await loadStatus(true);
        if (!fresh || !isStillRunning(fresh)) {
          if (timer) clearInterval(timer);
        }
      }, POLL_MS);
    };

    startPolling();

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [loadStatus, taskId]);

  if (!taskId) {
    return (
      <div className="page-content" style={{ maxWidth: 900, margin: '0 auto' }}>
        <p style={{ color: '#B91C1C' }}>Missing task ID in URL.</p>
        <Link to="/tasks" style={{ color: '#2563EB' }}>← Back to Tasks</Link>
      </div>
    );
  }

  return (
    <div className="page-content" style={{ maxWidth: 960, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em', color: '#0F172A' }}>
            📋 Task Status
          </h1>
          <p style={{ fontSize: 14, color: '#475569', margin: 0, lineHeight: 1.7 }}>
            Live view of orchestration progress, child tasks, and execution metadata.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
          <Link
            to="/tasks"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '8px 14px',
              borderRadius: 8,
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              color: '#2563EB',
              textDecoration: 'none',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            ← Tasks
          </Link>
          <button
            type="button"
            onClick={() => loadStatus(true)}
            disabled={refreshing}
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              background: refreshing ? '#BFDBFE' : '#2563EB',
              border: 'none',
              color: '#fff',
              fontWeight: 600,
              fontSize: 13,
              cursor: refreshing ? 'default' : 'pointer',
            }}
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {loading && !tree ? (
        <div style={{ padding: 28, background: '#F0F8FF', borderRadius: 14, textAlign: 'center', color: '#475569', border: '1px solid #DBEAFE' }}>
          Loading task status…
        </div>
      ) : tree ? (
        <>
          <TaskStatusView tree={tree} loading={refreshing} error={error} lastUpdated={lastUpdated} />
          <PageSection title="Agent thread visualizer">
            <ThreadVisualizer />
          </PageSection>
        </>
      ) : (
        <div style={{ padding: 28, background: '#FEF2F2', borderRadius: 14, color: '#991B1B', border: '1px solid #FECACA' }}>
          {error || 'Task not found'}
        </div>
      )}
    </div>
  );
};

export default TaskStatusPage;