import React from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';

const FRAMEWORKS = [
  { name: 'OKR', full: 'Objectives & Key Results', desc: 'Set ambitious objectives with measurable key results. Best for quarterly planning cycles.', color: '#7c6af7' },
  { name: 'SWOT', full: 'Strengths, Weaknesses, Opportunities, Threats', desc: 'Analyse internal capabilities and external forces before committing to a direction.', color: '#0891b2' },
  { name: 'RICE', full: 'Reach, Impact, Confidence, Effort', desc: 'Score and rank features or initiatives to prioritise the highest-leverage work.', color: '#d97706' },
  { name: 'Jobs-to-be-Done', full: 'JTBD Framework', desc: 'Define what "job" users hire your product to do — uncovers real motivations.', color: '#059669' },
  { name: 'North Star Metric', full: 'Single guiding KPI', desc: 'Identify the one metric that best captures delivered value to focus all teams.', color: '#be185d' },
];

const PROMPT_GROUPS = [
  {
    label: '📐 Frameworks',
    prompts: [
      'Write 3 OKRs for a B2B SaaS product team for Q3 2026.',
      'Run a SWOT analysis for a developer-tools startup entering an enterprise market.',
      'Use RICE scoring to rank these 5 features: [list them] — ask me for the list.',
      'Identify the North Star Metric for a marketplace app connecting freelancers with clients.',
    ],
  },
  {
    label: '🗺️ Roadmapping',
    prompts: [
      'Build a 6-month product roadmap for a data-analytics platform starting from zero.',
      'Create a phased migration plan from a monolith to microservices — 3 phases, 4 weeks each.',
      'Map out a technology adoption roadmap for adding LLM capabilities to an existing SaaS.',
      'Draft a quarterly roadmap that balances new features, tech debt, and compliance work.',
    ],
  },
  {
    label: '⚖️ Decision analysis',
    prompts: [
      'I need to choose between building in-house vs buying a third-party auth solution — help me decide.',
      'Compare the strategic risk of early monetisation vs growth-first approach for a B2C app.',
      'What are the second-order consequences of adopting a serverless architecture for our backend?',
      'Analyse the tradeoffs between TypeScript strictness levels for a large team.',
    ],
  },
  {
    label: '📈 Metrics & KPIs',
    prompts: [
      'Define KPIs for measuring the success of a developer experience improvement initiative.',
      'What metrics should a 10-person startup track in its first year of operation?',
      'Create a measurement framework for evaluating AI-generated code quality.',
      'Suggest leading indicators for customer churn in a subscription SaaS product.',
    ],
  },
  {
    label: '🤔 Competitive & market',
    prompts: [
      'Outline a competitive analysis framework for a new entry into the AI productivity market.',
      'What positioning strategy would differentiate a privacy-first AI assistant from OpenAI offerings?',
      'Identify the top 5 risks of entering the enterprise data-platform market in 2026.',
    ],
  },
];

const StrategyPage: React.FC = () => (
  <div style={{ padding: '28px 28px 60px', maxWidth: 950, margin: '0 auto', color: '#e2e8f0' }}>
    <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em' }}>🗺️ Strategy</h1>
    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: '0 0 28px', lineHeight: 1.7 }}>
      Use Concierge as your strategic thinking partner. Apply frameworks, build roadmaps, analyse
      decisions, and define the metrics that matter. Click any prompt to begin.
    </p>

    {/* framework cards */}
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 12px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Supported frameworks</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
        {FRAMEWORKS.map(({ name, full, desc, color }) => (
          <div key={name} style={{ background: 'rgba(255,255,255,0.025)', border: `1px solid ${color}33`, borderRadius: 9, padding: '14px 16px' }}>
            <div style={{ fontSize: 14, fontWeight: 800, color, marginBottom: 2 }}>{name}</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>{full}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5 }}>{desc}</div>
          </div>
        ))}
      </div>
    </div>

    {/* prompt groups */}
    {PROMPT_GROUPS.map(({ label, prompts }) => (
      <div key={label} style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 12px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{label}</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {prompts.map((p) => <SamplePrompt key={p} text={p} />)}
        </div>
      </div>
    ))}
  </div>
);

export default StrategyPage;