import type { TaskTree, TaskTreeNode } from '@/api/taskService';

export type WorkflowUpdateKind = 'started' | 'progress' | 'completed' | 'failed' | 'workflow_complete' | 'workflow_failed';

export interface WorkflowUpdate {
  id: string;
  threadId: string;
  stepId: string;
  stepName: string;
  kind: WorkflowUpdateKind;
  status: string;
  progress: number;
  summary?: string;
  timestamp: string;
}

export interface StepSnapshot {
  status: string;
  progress: number;
  name: string;
  summary?: string;
}

export type StepSnapshotMap = Record<string, StepSnapshot>;

const TERMINAL = new Set(['done', 'completed', 'success', 'error', 'failed', 'failure', 'killed']);

export function isTerminalStatus(status?: string) {
  return TERMINAL.has((status || '').toLowerCase());
}

export function stepDisplayName(node: TaskTreeNode) {
  const meta = node.metadata as { task_name?: string } | undefined;
  return node.task_name || meta?.task_name || node.task_id;
}

export function flattenStepSnapshots(tree: TaskTree): StepSnapshotMap {
  const out: StepSnapshotMap = {};
  const walk = (node: TaskTreeNode) => {
    if (node.task_id !== tree.task_id) {
      const meta = node.metadata as { task_name?: string; result_summary?: string } | undefined;
      out[node.task_id] = {
        status: node.status || node.state || 'unknown',
        progress: typeof node.progress === 'number' ? node.progress : 0,
        name: stepDisplayName(node),
        summary: meta?.result_summary ? String(meta.result_summary) : undefined,
      };
    }
    node.children?.forEach(walk);
  };
  walk(tree);
  return out;
}

export function workflowProgress(tree: TaskTree | null) {
  if (!tree?.children?.length) return { completed: 0, total: 0, percent: 0 };
  const total = tree.children.length;
  const completed = tree.children.filter((c) => isTerminalStatus(c.status || c.state)).length;
  const percent = total ? Math.round((completed / total) * 100) : 0;
  return { completed, total, percent };
}

export function diffStepSnapshots(
  threadId: string,
  prev: StepSnapshotMap,
  next: StepSnapshotMap,
): WorkflowUpdate[] {
  const updates: WorkflowUpdate[] = [];
  const now = new Date().toISOString();

  for (const [stepId, snap] of Object.entries(next)) {
    const before = prev[stepId];
    if (!before) {
      updates.push({
        id: `${threadId}:${stepId}:started:${now}`,
        threadId,
        stepId,
        stepName: snap.name,
        kind: 'started',
        status: snap.status,
        progress: snap.progress,
        timestamp: now,
      });
      continue;
    }
    if (before.status !== snap.status) {
      if (isTerminalStatus(snap.status) && ['done', 'completed', 'success'].includes(snap.status.toLowerCase())) {
        updates.push({
          id: `${threadId}:${stepId}:completed:${now}`,
          threadId,
          stepId,
          stepName: snap.name,
          kind: 'completed',
          status: snap.status,
          progress: snap.progress,
          summary: snap.summary,
          timestamp: now,
        });
      } else if (isTerminalStatus(snap.status)) {
        updates.push({
          id: `${threadId}:${stepId}:failed:${now}`,
          threadId,
          stepId,
          stepName: snap.name,
          kind: 'failed',
          status: snap.status,
          progress: snap.progress,
          summary: snap.summary,
          timestamp: now,
        });
      } else if (snap.progress > before.progress) {
        updates.push({
          id: `${threadId}:${stepId}:progress:${snap.progress}:${now}`,
          threadId,
          stepId,
          stepName: snap.name,
          kind: 'progress',
          status: snap.status,
          progress: snap.progress,
          timestamp: now,
        });
      }
    } else if (snap.progress > before.progress + 4) {
      updates.push({
        id: `${threadId}:${stepId}:progress:${snap.progress}:${now}`,
        threadId,
        stepId,
        stepName: snap.name,
        kind: 'progress',
        status: snap.status,
        progress: snap.progress,
        timestamp: now,
      });
    }
  }

  return updates;
}

export function formatWorkflowUpdateMessage(update: WorkflowUpdate) {
  switch (update.kind) {
    case 'started':
      return `▶ Started step: ${update.stepName}`;
    case 'progress':
      return `◔ ${update.stepName} — ${update.progress}%`;
    case 'completed':
      return update.summary
        ? `✅ Completed: ${update.stepName}\n${truncate(update.summary, 280)}`
        : `✅ Completed: ${update.stepName}`;
    case 'failed':
      return update.summary
        ? `❌ Failed: ${update.stepName}\n${truncate(update.summary, 200)}`
        : `❌ Failed: ${update.stepName}`;
    case 'workflow_complete':
      return update.summary
        ? `🎉 Workflow complete (${update.progress}%)\n${truncate(update.summary, 320)}`
        : `🎉 Workflow complete — all steps finished.`;
    case 'workflow_failed':
      return `⚠️ Workflow finished with errors. Check the task status page for details.`;
    default:
      return update.stepName;
  }
}

function truncate(text: string, max: number) {
  const t = text.trim();
  return t.length <= max ? t : `${t.slice(0, max - 1)}…`;
}

export function isWorkflowTerminal(tree: TaskTree) {
  const rootDone = isTerminalStatus(tree.status || tree.state) || tree.progress === 100;
  if (!tree.children?.length) return rootDone;
  const { completed, total } = workflowProgress(tree);
  return rootDone || (total > 0 && completed === total);
}