import React from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';

const PROMPT_GROUPS = [
  {
    label: '🚀 Launch & delivery',
    prompts: [
      'Create a 4-week goal to launch a public-facing REST API for our SaaS product.',
      'Plan the rollout of a new authentication system — list tasks, risks, and milestones.',
      'I need to ship a mobile MVP in 6 weeks. Break it into weekly goals.',
      'Map out the go-to-market plan for the v2.0 release.',
    ],
  },
  {
    label: '⚙️ Technical improvement',
    prompts: [
      'Set a goal to reduce CI/CD pipeline time from 12 minutes to under 5.',
      'Improve test coverage from 55% to 85% across all core modules in 3 weeks.',
      'Plan a database schema migration to support multi-tenancy.',
      'Reduce React bundle size by 30% — identify the biggest wins first.',
    ],
  },
  {
    label: '📊 Research & analysis',
    prompts: [
      'Research the top 3 alternatives to Qdrant for our vector store and produce a comparison.',
      'Analyse our Q1 sprint velocity data and recommend process improvements.',
      'Investigate why API p95 latency increased 40% after the last deploy.',
      'Survey industry best practices for LLM observability in 2026.',
    ],
  },
  {
    label: '🤝 Team & process',
    prompts: [
      'Create monthly goals for improving developer onboarding documentation.',
      'Plan a 2-week sprint to reduce the backlog of bug reports by 50%.',
      'Outline a knowledge-transfer plan for the outgoing lead engineer.',
      'Set team objectives for improving code review turnaround to under 24 hours.',
      'Design a promotional banner image for the goal.',
    ],
  },
  {
    label: '🖼️ Multimedia goals',
    prompts: [
      'Generate a logo for this goal/project.',
      'What multimedia assets would support this objective?',
    ],
  },
];

import ProcessingBanner from '@/components/ProcessingBanner';

const GoalsPage: React.FC = () => (
  <div style={{ padding: '28px 28px 60px', maxWidth: 900, margin: '0 auto', color: '#e2e8f0' }}>
    <ProcessingBanner />
    {/* header */}
    <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em' }}>
      🎯 Goals
    </h1>
    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: '0 0 32px', lineHeight: 1.7 }}>
      Goals are high-level outcomes. Describe what you want to achieve and Concierge will decompose
      it into a prioritised task tree, run specialist agents, and synthesise a final report.
      Click any prompt below to start a goal in the chat.
    </p>

    {/* how it works banner */}
    <div
      style={{
        background: 'rgba(124,106,247,0.08)',
        border: '1px solid rgba(124,106,247,0.2)',
        borderRadius: 10,
        padding: '16px 20px',
        marginBottom: 32,
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 12,
      }}
    >
      {[
        { step: '1', title: 'Describe outcome', desc: 'Be specific — include a timeframe and measurable result.' },
        { step: '2', title: 'Planner decomposes', desc: 'Goal → prioritised tasks with dependencies.' },
        { step: '3', title: 'Agents execute', desc: 'Research, Coding, and Critic agents run in parallel.' },
        { step: '4', title: 'Synthesizer reports', desc: 'Key points, risks, and recommendations returned.' },
      ].map(({ step, title, desc }) => (
        <div key={step}>
          <div style={{ fontSize: 11, color: '#7c6af7', fontWeight: 700, marginBottom: 2 }}>STEP {step}</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 }}>{title}</div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{desc}</div>
        </div>
      ))}
    </div>

    {/* prompt groups */}
    {PROMPT_GROUPS.map(({ label, prompts }) => (
      <div key={label} style={{ marginBottom: 28 }}>
        <h2
          style={{
            fontSize: 13,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'rgba(255,255,255,0.35)',
            margin: '0 0 12px',
            paddingBottom: 8,
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          {label}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {prompts.map((p) => <SamplePrompt key={p} text={p} />)}
        </div>
      </div>
    ))}
  </div>
);

export default GoalsPage;