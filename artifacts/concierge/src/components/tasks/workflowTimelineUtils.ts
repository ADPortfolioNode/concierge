import type { TaskTreeNode } from '@/api/taskService';
import { stepDisplayName } from '@/utils/workflowStatus';

export type StepPhase = 'done' | 'active' | 'upcoming' | 'failed';

export interface TimelineStep {
  node: TaskTreeNode;
  index: number;
  name: string;
  status: string;
  phase: StepPhase;
  progress: number;
}

const DONE = new Set(['done', 'completed', 'success']);
const ACTIVE = new Set(['running', 'started', 'progress', 'in_progress']);
const FAILED = new Set(['failed', 'error', 'failure', 'killed']);

export function stepPhase(status?: string, progress?: number): StepPhase {
  const s = (status || '').toLowerCase();
  if (FAILED.has(s)) return 'failed';
  if (DONE.has(s) || progress === 100) return 'done';
  if (ACTIVE.has(s)) return 'active';
  return 'upcoming';
}

export function flattenWorkflowSteps(root: TaskTreeNode): TimelineStep[] {
  const nodes: TaskTreeNode[] = [];
  const walk = (node: TaskTreeNode) => {
    if (node.task_id !== root.task_id) nodes.push(node);
    node.children?.forEach(walk);
  };
  walk(root);

  return nodes.map((node, index) => {
    const status = node.status || node.state || 'pending';
    const progress = typeof node.progress === 'number' ? node.progress : 0;
    return {
      node,
      index,
      name: stepDisplayName(node),
      status,
      phase: stepPhase(status, progress),
      progress,
    };
  });
}

export function currentStepIndex(steps: TimelineStep[]): number {
  const failed = steps.findIndex((s) => s.phase === 'failed');
  if (failed >= 0) return failed;
  const active = steps.findIndex((s) => s.phase === 'active');
  if (active >= 0) return active;
  const firstOpen = steps.findIndex((s) => s.phase === 'upcoming');
  if (firstOpen >= 0) return firstOpen;
  return Math.max(0, steps.length - 1);
}

export function timelineFillPercent(steps: TimelineStep[], currentIdx: number) {
  if (steps.length <= 1) return steps[0]?.phase === 'done' ? 100 : 0;
  const doneCount = steps.filter((s) => s.phase === 'done').length;
  if (doneCount === steps.length) return 100;
  const anchor = currentIdx + (steps[currentIdx]?.phase === 'done' ? 1 : 0.5);
  return Math.min(100, Math.max(0, (anchor / steps.length) * 100));
}

export const PHASE_COLORS: Record<StepPhase, string> = {
  done: '#059669',
  active: '#2563EB',
  upcoming: '#94A3B8',
  failed: '#DC2626',
};