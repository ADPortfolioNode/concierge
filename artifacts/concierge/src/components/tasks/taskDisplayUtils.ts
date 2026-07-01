export function normalizeGoalText(text?: string | null) {
  if (!text) return null;
  return text.replace(/^Goal:\s*/i, '').trim();
}

export function resolveTaskTitle(taskName?: string, goal?: string | null) {
  const fromGoal = normalizeGoalText(goal);
  const fromName = normalizeGoalText(taskName);
  return fromGoal || fromName || 'Untitled task';
}

export function truncateText(text: string, max: number) {
  const t = text.trim();
  return t.length <= max ? t : `${t.slice(0, max - 1)}…`;
}

export interface SummaryStep {
  label: string;
  body: string;
}

export function parseStepSummaries(summary: string): SummaryStep[] {
  const segments = summary.split(/\n\n+/).filter((s) => s.trim());
  const steps: SummaryStep[] = [];

  for (const seg of segments) {
    const match = seg.match(/^([^:\n]{3,80}):\s*([\s\S]*)$/);
    if (match) {
      steps.push({ label: match[1].trim(), body: match[2].trim() });
    } else if (steps.length === 0) {
      steps.push({ label: 'Summary', body: seg.trim() });
    } else {
      steps[steps.length - 1].body += `\n\n${seg.trim()}`;
    }
  }

  if (steps.length === 0 && summary.trim()) {
    return [{ label: 'Summary', body: summary.trim() }];
  }
  return steps;
}

export function pollingStatusLabel(terminal: boolean, refreshing: boolean) {
  if (refreshing) return 'Refreshing…';
  return terminal ? 'Complete' : 'Live updates';
}