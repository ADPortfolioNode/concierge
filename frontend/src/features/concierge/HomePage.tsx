import React from 'react';
import { Link } from 'react-router-dom';
import SamplePrompt from '@/components/primitives/SamplePrompt';

// ── capability definitions ────────────────────────────────────────────────
const CAPABILITIES = [
  {
    icon: '💬',
    title: 'Conversational AI',
    description:
      'Chat with an LLM-backed orchestrator. Ask questions, brainstorm ideas, or have it explain concepts in plain language.',
    color: '#7c6af7',
    prompts: [
      'Explain the difference between RAG and fine-tuning in plain English.',
      'What are the pros and cons of using a microservices architecture?',
      'Help me write a professional email declining a vendor proposal.',
    ],
  },
  {
    icon: '🎯',
    title: 'Goal Planning',
    description:
      'Set high-level outcomes. Concierge decomposes them into prioritised tasks, tracks progress, and surfaces blockers.',
    color: '#0891b2',
    link: '/goals',
    prompts: [
      'Create a 4-week goal to migrate our REST API to GraphQL.',
      'I want to reduce page load time by 40% — plan it out.',
      'Set weekly goals for improving test coverage from 60% to 90%.',
      'Design a banner image for the goal.',
    ],
  },
  {
    icon: '✅',
    title: 'Task Orchestration',
    description:
      'Run background tasks: read & analyse files, generate code, analyse datasets, and write results — all asynchronously.',
    color: '#059669',
    link: '/tasks',
    prompts: [
      'Analyse the CSV I just uploaded and summarise the key trends.',
      'Generate a Python script to parse JSON logs and extract error counts.',
      'Read my uploaded spec and list all the missing edge cases.',
      'Create an image illustrating the analysis results.',
    ],
  },
  {
    icon: '📁',
    title: 'Workspace & Files',
    description:
      'Upload documents, images, CSVs, PDFs, and more. Attach them to projects and reference them in any prompt.',
    color: '#d97706',
    link: '/workspace',
    prompts: [
      'I\'ve uploaded a PDF spec — summarise the authentication requirements.',
      'Attach the financial model CSV to the Q2 Planning project.',
      'Extract all the TODO comments from the uploaded source file.',
      'Show me the image I just uploaded.',
      'Transcribe the audio file I uploaded and summarise it.',
    ],
  },
  {
    icon: '🧠',
    title: 'Memory & Context',
    description:
      'Concierge stores summaries in a vector graph. Past conversations inform future answers — automatically.',
    color: '#be185d',
    prompts: [
      'What decisions did we make about the database schema last session?',
      'Remind me what the critic agent approved in the last autonomous run.',
      'What was the outcome of the Q1 strategy planning session?',
    ],
  },
  {
    icon: '🔌',
    title: 'Plugins & Integrations',
    description:
      'Extend the orchestrator with registered tools, plugins, and external service integrations.',
    color: '#7c3aed',
    link: '/capabilities',
    prompts: [
      'What plugins are currently registered and enabled?',
      'Run the web search tool for "latest LLM benchmarks 2026".',
      'Which integrations are available and what do they connect to?',
    ],
  },
];

// ── reusable section heading ──────────────────────────────────────────────
const SectionHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2
    style={{
      fontSize: 13,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      color: 'rgba(255,255,255,0.35)',
      margin: '0 0 16px',
      paddingBottom: 8,
      borderBottom: '1px solid rgba(255,255,255,0.06)',
    }}
  >
    {children}
  </h2>
);

// ── capability card ───────────────────────────────────────────────────────
const CapCard: React.FC<(typeof CAPABILITIES)[0]> = ({
  icon,
  title,
  description,
  color,
  link,
  prompts,
}) => (
  <div
    style={{
      background: 'rgba(255,255,255,0.025)',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 10,
      padding: '20px 20px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}
  >
    {/* header */}
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span
        style={{
          fontSize: 22,
          lineHeight: 1,
          background: `${color}22`,
          border: `1px solid ${color}44`,
          borderRadius: 8,
          padding: '6px 8px',
        }}
      >
        {icon}
      </span>
      <div>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#e2e8f0' }}>{title}</div>
        {link && (
          <Link
            to={link}
            style={{ fontSize: 11, color: color, textDecoration: 'none', opacity: 0.85 }}
          >
            Open page →
          </Link>
        )}
      </div>
    </div>

    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.55)', margin: 0, lineHeight: 1.6 }}>
      {description}
    </p>

    {/* sample prompts */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        Sample prompts
      </div>
      {prompts.map((p) => (
        <SamplePrompt key={p} text={p} variant="chip" />
      ))}
    </div>
  </div>
);

// ── main page ─────────────────────────────────────────────────────────────
const HomePage: React.FC = () => (
  <div
    style={{
      padding: '28px 28px 48px',
      maxWidth: 1100,
      margin: '0 auto',
      color: '#e2e8f0',
    }}
  >
    {/* hero */}
    <div style={{ marginBottom: 36 }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
        Welcome to <span style={{ color: '#7c6af7' }}>Concierge</span>
      </h1>
      <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.5)', margin: 0, maxWidth: 600 }}>
        An AI orchestrator powered by GPT-4o. Click any sample prompt to prefill the chat,
        or type your own in the panel on the left.
      </p>
    </div>

    {/* quick-start chips */}
    <div style={{ marginBottom: 36 }}>
      <SectionHeading>Quick start</SectionHeading>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {[
          'Hello — what can you do?',
          'Summarise what you know about my last project.',
          'Create a 2-week sprint plan for a new feature.',
          'What tasks are currently queued?',
          'Upload a file and analyse it.',
        ].map((p) => (
          <SamplePrompt key={p} text={p} variant="chip" />
        ))}
      </div>
    </div>

    {/* capabilities grid */}
    <div style={{ marginBottom: 36 }}>
      <SectionHeading>Capabilities & example prompts</SectionHeading>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))',
          gap: 16,
        }}
      >
        {CAPABILITIES.map((cap) => (
          <CapCard key={cap.title} {...cap} />
        ))}
      </div>
    </div>

    {/* navigation shortcuts */}
    <div>
      <SectionHeading>Explore the app</SectionHeading>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
        {[
          { to: '/goals',        label: '🎯 Goals' },
          { to: '/tasks',        label: '✅ Tasks' },
          { to: '/workspace',    label: '📁 Workspace' },
          { to: '/strategy',     label: '🗺️ Strategy' },
          { to: '/capabilities', label: '🔌 Capabilities' },
          { to: '/howto',        label: '📖 How-To Guide' },
        ].map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            style={{
              display: 'inline-block',
              padding: '8px 18px',
              borderRadius: 8,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#d4d0ff',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  </div>
);

export default HomePage;
