import React, { useEffect, useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { makeApiUrl } from '@/config/activeServer';

// ── types ────────────────────────────────────────────────────────────────────

interface Chip {
  label: string;
  value: string | number;
  color?: string;   // dot color
  mono?: boolean;   // monospace value
}

interface BarState {
  title: string;
  icon: string;
  chips: Chip[];
  footer?: string;
  loading: boolean;
}

// ── helpers ──────────────────────────────────────────────────────────────────

const STATUS_DOT: Record<string, string> = {
  running: '#22c55e',
  started: '#22c55e',
  queued: '#f59e0b',
  pending: '#f59e0b',
  completed: '#38bdf8',
  success: '#38bdf8',
  done: '#38bdf8',
  error: '#ef4444',
  failed: '#ef4444',
};

const statusColor = (s: string) => STATUS_DOT[s?.toLowerCase()] ?? '#94a3b8';

const shortId = (id: string) => (id?.length > 10 ? id.slice(0, 8) + '…' : id);

const timeSince = (iso?: string) => {
  if (!iso) return null;
  const delta = Math.max(0, Date.now() - new Date(iso).getTime());
  const s = Math.floor(delta / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
};

async function apiFetch(path: string): Promise<unknown> {
  const r = await fetch(makeApiUrl(path));
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ── per-route fetchers ────────────────────────────────────────────────────────

async function fetchHomeBar(): Promise<Partial<BarState>> {
  const [metricsRes, timelineRes] = await Promise.allSettled([
    apiFetch('/api/v1/concierge/metrics'),
    apiFetch('/api/v1/concierge/timeline'),
  ]);

  const metrics = metricsRes.status === 'fulfilled' ? (metricsRes.value as any)?.data : null;
  const plan    = timelineRes.status === 'fulfilled' ? (timelineRes.value as any)?.data : null;
  const tasks: any[] = plan?.tasks ?? [];
  const running = tasks.filter((t: any) => ['running','started'].includes(t.status ?? '')).length;

  const chips: Chip[] = [];
  if (metrics?.total_requests != null) chips.push({ label: 'Requests', value: metrics.total_requests });
  chips.push({ label: 'Tasks', value: tasks.length });
  if (running > 0) chips.push({ label: 'Active', value: running, color: '#22c55e' });
  if (metrics?.failovers) chips.push({ label: 'Fallbacks', value: metrics.failovers, color: '#f59e0b' });

  const footer = metrics?.summary ?? (tasks.length ? `${tasks.length} task${tasks.length !== 1 ? 's' : ''} in plan` : 'No active plan');
  return { chips, footer };
}

async function fetchGoalsBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/concierge/timeline');
  const plan = (res as any)?.data;
  const tasks: any[] = plan?.tasks ?? [];

  const statusCounts: Record<string, number> = {};
  tasks.forEach((t: any) => {
    const s = t.status ?? 'pending';
    statusCounts[s] = (statusCounts[s] ?? 0) + 1;
  });

  const chips: Chip[] = [{ label: 'Goals', value: tasks.length }];
  Object.entries(statusCounts).forEach(([s, n]) => {
    chips.push({ label: s.charAt(0).toUpperCase() + s.slice(1), value: n, color: statusColor(s) });
  });

  const lastGoal = tasks[tasks.length - 1];
  const footer = lastGoal
    ? `Latest: ${lastGoal.title ?? lastGoal.instructions ?? lastGoal.task_id ?? 'goal'}`
    : 'No goals in plan yet — start one in the chat';

  return { chips, footer };
}

async function fetchStrategyBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/concierge/timeline');
  const plan = (res as any)?.data;
  const tasks: any[] = plan?.tasks ?? [];
  const phases = [...new Set(tasks.map((t: any) => t.phase).filter(Boolean))];
  const chips: Chip[] = [
    { label: 'Plan tasks', value: tasks.length },
    ...(phases.length ? [{ label: 'Phases', value: phases.length }] : []),
  ];
  const running = tasks.filter((t: any) => ['running','started'].includes(t.status ?? '')).length;
  if (running) chips.push({ label: 'Active', value: running, color: '#22c55e' });
  const footer = plan?.plan_id
    ? `Plan ID: ${shortId(plan.plan_id)}`
    : tasks.length
    ? `${tasks.length} strategy task${tasks.length !== 1 ? 's' : ''} loaded`
    : 'No strategy plan active';
  return { chips, footer };
}

async function fetchTasksBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/tasks');
  const tasks: any[] = (res as any)?.data ?? [];

  const running  = tasks.filter((t: any) => ['running','STARTED'].includes(t.status ?? t.statusObj?.status ?? '')).length;
  const queued   = tasks.filter((t: any) => ['queued','PENDING'].includes(t.status ?? t.statusObj?.status ?? '')).length;
  const done     = tasks.filter((t: any) => ['completed','done','success'].includes(t.status ?? t.statusObj?.status ?? '')).length;
  const failed   = tasks.filter((t: any) => ['error','failed','FAILURE'].includes(t.status ?? t.statusObj?.status ?? '')).length;

  const chips: Chip[] = [
    { label: 'Total', value: tasks.length },
    ...(running ? [{ label: 'Running', value: running, color: '#22c55e' }] : []),
    ...(queued  ? [{ label: 'Queued',  value: queued,  color: '#f59e0b' }] : []),
    ...(done    ? [{ label: 'Done',    value: done,    color: '#38bdf8' }] : []),
    ...(failed  ? [{ label: 'Failed',  value: failed,  color: '#ef4444' }] : []),
  ];

  // thread associations: unique task_thread_id values
  const threads: string[] = [...new Set(
    tasks.map((t: any) => t.task_thread_id ?? t.thread_id).filter(Boolean) as string[]
  )];
  if (threads.length) chips.push({ label: 'Threads', value: threads.length });

  const footer = threads.length
    ? `Thread${threads.length !== 1 ? 's' : ''}: ${threads.slice(0, 2).map(shortId).join(', ')}${threads.length > 2 ? ` +${threads.length - 2}` : ''}`
    : tasks.length ? `${tasks.length} task record${tasks.length !== 1 ? 's' : ''} tracked` : 'No tasks — submit one to get started';

  return { chips, footer };
}

async function fetchWorkspaceBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/concierge/conversation');
  const msgs: any[] = (res as any)?.data ?? [];
  const human = msgs.filter((m: any) => m.role === 'human' || m.role === 'user').length;
  const ai    = msgs.filter((m: any) => m.role === 'ai' || m.role === 'assistant').length;
  const last  = msgs[msgs.length - 1];
  const chips: Chip[] = [
    { label: 'Messages', value: msgs.length },
    { label: 'You', value: human },
    { label: 'AI', value: ai },
  ];
  const footer = last
    ? `Last message ${timeSince(last.timestamp ?? last.created_at) ?? 'this session'}`
    : 'No conversation history yet';
  return { chips, footer };
}

async function fetchMediaBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/concierge/media');
  const items: any[] = (res as any)?.data?.items ?? (res as any)?.data ?? [];
  const chips: Chip[] = [{ label: 'Files', value: items.length }];
  const last  = items[items.length - 1];
  const footer = last
    ? `Latest: ${last.filename ?? last.name ?? 'media file'} · ${timeSince(last.metadata?.created_at ?? last.mtime ?? last.created_at) ?? ''}`
    : 'No media generated yet — ask Concierge to create an image';
  return { chips, footer };
}

async function fetchCapabilitiesBar(): Promise<Partial<BarState>> {
  const res = await apiFetch('/api/v1/capabilities');
  const data = (res as any)?.data ?? {};
  const tools   = (data.tools         ?? []).length;
  const plugins = (data.plugins        ?? []).length;
  const intgs   = (data.integrations   ?? []).length;
  const enabled = [
    ...(data.tools        ?? []),
    ...(data.plugins      ?? []),
    ...(data.integrations ?? []),
  ].filter((x: any) => x.enabled !== false).length;

  const chips: Chip[] = [
    { label: 'Tools', value: tools },
    { label: 'Plugins', value: plugins },
    { label: 'Integrations', value: intgs },
    { label: 'Enabled', value: enabled, color: '#22c55e' },
  ];
  return { chips, footer: `${tools + plugins + intgs} total capabilities registered` };
}

// ── per-route config ─────────────────────────────────────────────────────────

interface RouteConfig {
  title: string;
  icon: string;
  fetch: () => Promise<Partial<BarState>>;
  refreshMs: number;
}

const ROUTES: Record<string, RouteConfig> = {
  '/':             { title: 'Dashboard',    icon: '🏠', fetch: fetchHomeBar,         refreshMs: 12000 },
  '/goals':        { title: 'Goals',        icon: '🎯', fetch: fetchGoalsBar,        refreshMs: 15000 },
  '/strategy':     { title: 'Strategy',     icon: '🗺️', fetch: fetchStrategyBar,     refreshMs: 15000 },
  '/tasks':        { title: 'Tasks',        icon: '⚡', fetch: fetchTasksBar,        refreshMs: 6000  },
  '/workspace':    { title: 'Workspace',    icon: '📁', fetch: fetchWorkspaceBar,    refreshMs: 20000 },
  '/media':        { title: 'Media',        icon: '🖼️', fetch: fetchMediaBar,        refreshMs: 15000 },
  '/howto':        { title: 'Guide',        icon: '📖', fetch: async () => ({ chips: [], footer: 'Tips and tutorials for using Concierge effectively.' }) , refreshMs: 0 },
  '/capabilities': { title: 'Integrations', icon: '🔌', fetch: fetchCapabilitiesBar, refreshMs: 60000 },
};

// ── component ────────────────────────────────────────────────────────────────

const PageMetaBar: React.FC = () => {
  const { pathname } = useLocation();
  const route = ROUTES[pathname] ?? ROUTES['/'];

  const [bar, setBar] = useState<BarState>({
    title: route.title,
    icon: route.icon,
    chips: [],
    footer: undefined,
    loading: true,
  });

  const load = useCallback(async () => {
    setBar(prev => ({ ...prev, loading: true }));
    try {
      const partial = await route.fetch();
      setBar({
        title: route.title,
        icon: route.icon,
        chips: partial.chips ?? [],
        footer: partial.footer,
        loading: false,
      });
    } catch {
      setBar(prev => ({ ...prev, loading: false }));
    }
  }, [route]);

  useEffect(() => {
    load();
    if (!route.refreshMs) return;
    const iv = setInterval(load, route.refreshMs);
    return () => clearInterval(iv);
  }, [load, route.refreshMs]);

  return (
    <div
      style={{
        padding: '7px 14px 6px',
        borderBottom: '1px solid #DBEAFE',
        background: '#F8FAFF',
        flexShrink: 0,
      }}
    >
      {/* row 1: page label + chips */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#2563EB', letterSpacing: '0.07em', textTransform: 'uppercase', marginRight: 2 }}>
          {route.icon} {route.title}
        </span>

        {bar.loading && bar.chips.length === 0 ? (
          <span style={{ fontSize: 10, color: '#94A3B8' }}>loading…</span>
        ) : (
          bar.chips.map((chip, i) => (
            <span
              key={i}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 600,
                background: '#EFF6FF',
                border: '1px solid #DBEAFE',
                borderRadius: 999,
                padding: '1px 7px',
                color: '#1E40AF',
                whiteSpace: 'nowrap',
              }}
            >
              {chip.color && (
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: chip.color,
                    flexShrink: 0,
                    boxShadow: `0 0 4px ${chip.color}80`,
                  }}
                />
              )}
              <span style={{ color: '#64748B', fontWeight: 500 }}>{chip.label}</span>
              <span style={{ fontFamily: chip.mono ? 'monospace' : undefined, color: '#0F172A' }}>{chip.value}</span>
            </span>
          ))
        )}

        {bar.loading && bar.chips.length > 0 && (
          <span style={{ fontSize: 9, color: '#94A3B8', marginLeft: 2 }}>↻</span>
        )}
      </div>

      {/* row 2: footer / latest item */}
      {bar.footer && (
        <div
          style={{
            fontSize: 10,
            color: '#64748B',
            marginTop: 3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {bar.footer}
        </div>
      )}
    </div>
  );
};

export default PageMetaBar;
