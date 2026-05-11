import React, { useMemo } from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';
import { useAppStore } from '@/state/appStore';

const TEAM_PHOTO =
  'https://thumbs.dreamstime.com/b/young-smiling-business-people-working-office-group-coworkers-sitting-together-table-laptops-modern-teamwork-124959227.jpg';

// ── node + edge definitions for the architecture diagram ─────────────────
const NODES = [
  { id: 'input',    x: 240, y: 28,  r: 18, label: 'User Goal',      sub: 'Natural language input',  color: '#64748B', glow: false },
  { id: 'root',     x: 240, y: 118, r: 30, label: 'Sacred Timeline', sub: 'Root Orchestrator',       color: '#2563EB', glow: true  },
  { id: 'planner',  x: 240, y: 208, r: 22, label: 'Planner',         sub: 'Goal → task tree',        color: '#38BDF8', glow: false },
  { id: 'research', x: 72,  y: 298, r: 20, label: 'Research',        sub: 'RAG · Web search',        color: '#22C55E', glow: false },
  { id: 'coding',   x: 240, y: 298, r: 20, label: 'Coding',          sub: 'Generate · Execute',      color: '#F97316', glow: false },
  { id: 'critic',   x: 400, y: 298, r: 20, label: 'Critic',          sub: 'Evaluate · Refine',       color: '#EC4899', glow: false },
  { id: 'synth',    x: 240, y: 388, r: 22, label: 'Synthesizer',     sub: 'Merge · Output',          color: '#8B5CF6', glow: false },
] as const;

type NodeId = typeof NODES[number]['id'];

const NODE_MAP = Object.fromEntries(NODES.map((n) => [n.id, n])) as Record<NodeId, typeof NODES[number]>;

interface EdgeDef { from: NodeId; to: NodeId; delay: number; dashed?: boolean }

const EDGES: EdgeDef[] = [
  { from: 'input',    to: 'root',     delay: 0    },
  { from: 'root',     to: 'planner',  delay: 0.4  },
  { from: 'planner',  to: 'research', delay: 0.8  },
  { from: 'planner',  to: 'coding',   delay: 1.0  },
  { from: 'planner',  to: 'critic',   delay: 1.2  },
  { from: 'research', to: 'synth',    delay: 1.6  },
  { from: 'coding',   to: 'synth',    delay: 1.8  },
  { from: 'critic',   to: 'synth',    delay: 2.0  },
];

function edgePath(from: typeof NODES[number], to: typeof NODES[number]): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const cpOffset = Math.min(Math.abs(dy) * 0.45, 60);
  const cp1x = from.x + dx * 0.1;
  const cp1y = from.y + cpOffset;
  const cp2x = to.x - dx * 0.1;
  const cp2y = to.y - cpOffset;
  return `M ${from.x} ${from.y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${to.x} ${to.y}`;
}

// ── component ─────────────────────────────────────────────────────────────
const SacredTimelineHero: React.FC = () => {
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const taskThreadId = useAppStore((s) => s.taskThreadId);

  const taskCount = useMemo(() => {
    if (!timelinePlan) return 0;
    const tasks = timelinePlan?.tasks ?? timelinePlan?.plan?.tasks ?? [];
    return Array.isArray(tasks) ? tasks.length : 0;
  }, [timelinePlan]);

  return (
    <section className="stl-hero">
      {/* ── left: text ── */}
      <div className="stl-hero__text">
        <p className="stl-hero__eyebrow">Agentic Orchestration Engine</p>
        <h1 className="stl-hero__title">
          Your AI<br />
          <span className="stl-hero__title-accent">Concierge</span>
        </h1>
        <p className="stl-hero__subtitle">
          One orchestrator. A planner, a memory store, and specialized agents — research,
          coding, and critic — working in sequence to turn your goal into a result.
        </p>

        {taskThreadId ? (
          <div className="stl-hero__live-badge">
            <span className="stl-hero__live-dot" />
            <span>Active thread &mdash; {taskCount} task{taskCount !== 1 ? 's' : ''} in timeline</span>
          </div>
        ) : (
          <div className="stl-hero__live-badge stl-hero__live-badge--idle">
            <span className="stl-hero__live-dot stl-hero__live-dot--idle" />
            <span>Orchestrator ready &mdash; describe a goal to begin</span>
          </div>
        )}

        <div className="stl-hero__prompts">
          <SamplePrompt text="Build a 4-week sprint plan for a new API" variant="chip" />
          <SamplePrompt text="Research the best vector DB options in 2025" variant="chip" />
          <SamplePrompt text="Write a Python script to process my uploaded CSV" variant="chip" />
        </div>
      </div>

      {/* ── right: real photo + animated diagram ── */}
      <div style={{ position: 'relative', zIndex: 1 }}>
        {/* real people photo */}
        <div className="stl-hero__photo-panel">
          <img
            src={TEAM_PHOTO}
            alt="Team collaborating with AI concierge"
            loading="lazy"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
          <div className="stl-hero__photo-overlay">
            <span className="stl-hero__photo-caption">Teams achieving more with AI assistance</span>
          </div>
        </div>

        {/* floating agent diagram badge */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            bottom: -16,
            right: -16,
            background: '#FFFFFF',
            border: '1px solid #BFDBFE',
            borderRadius: 16,
            padding: '12px 16px',
            boxShadow: '0 8px 28px rgba(37,99,235,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <svg width="52" height="52" viewBox="0 0 480 430" style={{ width: 52, height: 52 }}>
            <defs>
              <filter id="stl-glow-badge" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>
            {EDGES.slice(0, 5).map((edge) => {
              const from = NODE_MAP[edge.from];
              const to = NODE_MAP[edge.to];
              return (
                <line
                  key={`${edge.from}-${edge.to}`}
                  x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                  stroke={to.color} strokeWidth="3" opacity="0.3"
                />
              );
            })}
            {NODES.map((node) => (
              <circle
                key={node.id}
                cx={node.x} cy={node.y} r={node.r * 0.9}
                fill={node.id === 'root' ? node.color : '#FFFFFF'}
                stroke={node.color}
                strokeWidth={node.id === 'root' ? 0 : 2}
                filter={node.glow ? 'url(#stl-glow-badge)' : undefined}
                opacity={node.id === 'root' ? 0.9 : 0.8}
              />
            ))}
          </svg>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', lineHeight: 1.2 }}>7 agents</div>
            <div style={{ fontSize: 10, color: '#38BDF8', fontWeight: 600 }}>live orchestration</div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SacredTimelineHero;
