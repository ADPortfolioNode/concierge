import React, { useMemo } from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';
import { useAppStore } from '@/state/appStore';

// ── node + edge definitions for the architecture diagram ─────────────────
const NODES = [
  { id: 'input',    x: 240, y: 28,  r: 18, label: 'User Goal',      sub: 'Natural language input',  color: '#94a3b8', glow: false },
  { id: 'root',     x: 240, y: 118, r: 30, label: 'Sacred Timeline', sub: 'Root Orchestrator',       color: '#7c6af7', glow: true  },
  { id: 'planner',  x: 240, y: 208, r: 22, label: 'Planner',         sub: 'Goal → task tree',        color: '#38bdf8', glow: false },
  { id: 'research', x: 72,  y: 298, r: 20, label: 'Research',        sub: 'RAG · Web search',        color: '#22c55e', glow: false },
  { id: 'coding',   x: 240, y: 298, r: 20, label: 'Coding',          sub: 'Generate · Execute',      color: '#f97316', glow: false },
  { id: 'critic',   x: 400, y: 298, r: 20, label: 'Critic',          sub: 'Evaluate · Refine',       color: '#ec4899', glow: false },
  { id: 'synth',    x: 240, y: 388, r: 22, label: 'Synthesizer',     sub: 'Merge · Output',          color: '#8b5cf6', glow: false },
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

// Compute a cubic bezier control-point path between two nodes
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
          Sacred<br />
          <span className="stl-hero__title-accent">Timeline</span>
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

      {/* ── right: animated architecture diagram ── */}
      <div className="stl-hero__diagram" aria-hidden="true">
        <svg
          viewBox="0 0 480 430"
          className="stl-hero__svg"
          xmlns="http://www.w3.org/2000/svg"
          role="img"
          aria-label="Sacred Timeline orchestrator architecture"
        >
          <defs>
            {/* glow filter for the orchestrator node */}
            <filter id="stl-glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="stl-glow-sm" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* gradient for edge lines */}
            {EDGES.map((edge) => {
              const from = NODE_MAP[edge.from];
              const to   = NODE_MAP[edge.to];
              return (
                <linearGradient
                  key={`grad-${edge.from}-${edge.to}`}
                  id={`stl-edge-grad-${edge.from}-${edge.to}`}
                  x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                  gradientUnits="userSpaceOnUse"
                >
                  <stop offset="0%"   stopColor={from.color} stopOpacity="0.6" />
                  <stop offset="100%" stopColor={to.color}   stopOpacity="0.6" />
                </linearGradient>
              );
            })}
          </defs>

          {/* ── edges ── */}
          {EDGES.map((edge) => {
            const from = NODE_MAP[edge.from];
            const to   = NODE_MAP[edge.to];
            const d    = edgePath(from, to);
            const gradId = `stl-edge-grad-${edge.from}-${edge.to}`;
            const pathId = `stl-path-${edge.from}-${edge.to}`;
            return (
              <g key={pathId}>
                {/* static track */}
                <path
                  d={d}
                  fill="none"
                  stroke={`url(#${gradId})`}
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  opacity="0.35"
                />
                {/* animated particle */}
                <circle r="3.5" fill={to.color} opacity="0.9" filter="url(#stl-glow-sm)">
                  <animateMotion
                    dur="2.4s"
                    begin={`${edge.delay}s`}
                    repeatCount="indefinite"
                    calcMode="spline"
                    keySplines="0.4 0 0.6 1"
                    keyTimes="0;1"
                  >
                    <mpath xlinkHref={`#${pathId}`} />
                  </animateMotion>
                </circle>
                {/* invisible path for animateMotion to reference */}
                <path id={pathId} d={d} fill="none" stroke="none" />
              </g>
            );
          })}

          {/* ── nodes ── */}
          {NODES.map((node) => {
            const isOrchestrator = node.id === 'root';
            const isInput        = node.id === 'input';
            return (
              <g key={node.id} className="stl-node-group">
                {/* outer pulse ring for orchestrator */}
                {isOrchestrator && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.r + 14}
                    fill="none"
                    stroke={node.color}
                    strokeWidth="1.5"
                    opacity="0.2"
                    className="stl-pulse-ring"
                  />
                )}
                {/* node body */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.r}
                  fill={isInput ? 'rgba(15,23,42,0.7)' : 'rgba(15,23,42,0.92)'}
                  stroke={node.color}
                  strokeWidth={isOrchestrator ? 2.5 : 1.5}
                  filter={isOrchestrator ? 'url(#stl-glow)' : undefined}
                />
                {/* icon dot (inner fill) */}
                {!isInput && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isOrchestrator ? 12 : 8}
                    fill={node.color}
                    opacity={isOrchestrator ? 0.75 : 0.55}
                  />
                )}
                {/* label */}
                <text
                  x={node.x}
                  y={node.y + node.r + 14}
                  textAnchor="middle"
                  fill={node.color}
                  fontSize={isOrchestrator ? 13 : 11}
                  fontWeight={isOrchestrator ? 700 : 600}
                  fontFamily="Inter, system-ui, sans-serif"
                  opacity="0.95"
                >
                  {node.label}
                </text>
                {/* sub-label */}
                <text
                  x={node.x}
                  y={node.y + node.r + 26}
                  textAnchor="middle"
                  fill="rgba(148,163,184,0.55)"
                  fontSize="9"
                  fontFamily="Inter, system-ui, sans-serif"
                >
                  {node.sub}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
};

export default SacredTimelineHero;
