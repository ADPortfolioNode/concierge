import React, { useState } from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';

// ── reusable components ──────────────────────────────────────────────────────
const H1: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em', color: '#e2e8f0' }}>{children}</h1>
);
const H2: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2 style={{ fontSize: 17, fontWeight: 700, margin: '32px 0 12px', color: '#c4b8ff', display: 'flex', alignItems: 'center', gap: 8 }}>{children}</h2>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 style={{ fontSize: 14, fontWeight: 700, margin: '20px 0 8px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{children}</h3>
);
const P: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.6)', lineHeight: 1.7, margin: '0 0 12px' }}>{children}</p>
);
const Step: React.FC<{ n: number; title: string; children: React.ReactNode }> = ({ n, title, children }) => (
  <div style={{ display: 'flex', gap: 14, marginBottom: 16 }}>
    <div style={{ minWidth: 28, height: 28, borderRadius: '50%', background: '#7c6af7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color: '#fff', flexShrink: 0, marginTop: 2 }}>{n}</div>
    <div><div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14, marginBottom: 4 }}>{title}</div>{children}</div>
  </div>
);
const Callout: React.FC<{ icon?: string; children: React.ReactNode }> = ({ icon = '💡', children }) => (
  <div style={{ background: 'rgba(124,106,247,0.1)', border: '1px solid rgba(124,106,247,0.25)', borderRadius: 8, padding: '12px 16px', fontSize: 13, color: '#c4b8ff', lineHeight: 1.6, margin: '12px 0' }}>
    {icon} {children}
  </div>
);

// ── collapsible section ──────────────────────────────────────────────────────
const Section: React.FC<{ title: string; defaultOpen?: boolean; children: React.ReactNode }> = ({
  title, defaultOpen = true, children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section style={{ marginBottom: 8, border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, overflow: 'hidden' }}>
      <button
        onClick={() => setOpen((x) => !x)}
        style={{ all: 'unset', width: '100%', padding: '14px 20px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.025)', fontSize: 15, fontWeight: 700, color: '#e2e8f0' }}
      >
        {title}
        <span style={{ fontSize: 12, opacity: 0.5 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && <div style={{ padding: '16px 20px 20px' }}>{children}</div>}
    </section>
  );
};

// ── page ─────────────────────────────────────────────────────────────────────
const HowToPage: React.FC = () => (
  <div style={{ padding: '28px 28px 60px', maxWidth: 820, margin: '0 auto', color: '#e2e8f0' }}>
    <H1>📖 How to Use Concierge</H1>
    <P>This guide walks you through the core workflows: chatting, setting Goals, running Tasks, and organising your Workspace.</P>

    {/* ── CHAT ── */}
    <Section title="💬 Chat — Getting answers instantly">
      <P>The chat panel (always visible on the left) is your primary interface. Type freely — Concierge decides whether to answer directly or kick off an autonomous agent run.</P>
      <H3>How it works</H3>
      <Step n={1} title="Type a message and press Enter">
        <P>Simple questions and conversational input return immediately. The response streams token-by-token so you see it as it's generated.</P>
      </Step>
      <Step n={2} title="Complex goals trigger the orchestrator">
        <P>When the planner detects something multi-step (e.g. "plan a migration"), it spins up specialist agents (Research, Coding, Critic, Synthesizer) in parallel and streams progress back.</P>
      </Step>
      <Step n={3} title="Attach a file to give the AI context">
        <P>Click the 📎 button to upload a document, CSV, image, or PDF. A file reference is automatically prepended to your message.</P>
      </Step>
      <Callout>All sample prompts on every page are clickable — they prefill the chat input so you can edit before sending.</Callout>
      <H3>Sample prompts</H3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          'Hello — what can you help me with today?',
      'Generate an image of a smiling cat.',
      'Transcribe audio or describe a video clip.',
          'Give me pros and cons of GraphQL vs REST for a mobile app.',
          'Write a haiku about async programming.',
          'What was the last goal we worked on?',
          'Explain what a vector database is in one paragraph.',
        ].map((p) => <SamplePrompt key={p} text={p} />)}
      </div>
    </Section>

    {/* ── GOALS ── */}
    <Section title="🎯 Goals — Planning outcomes">
      <P>Goals represent high-level outcomes you want to achieve. Concierge decomposes a goal into a task tree, estimates priorities, and tracks completion.</P>
      <H2>Lifecycle of a goal</H2>
      <Step n={1} title="Describe the outcome (not the steps)">
        <P>Be specific about the <em>what</em>, not the <em>how</em>. "Reduce API latency by 40% in 3 weeks" beats "optimise the backend".</P>
      </Step>
      <Step n={2} title="Concierge plans it">
        <P>The Planner agent breaks your goal into prioritised tasks, assigns each one a depth level, and detects dependencies.</P>
      </Step>
      <Step n={3} title="Agents run in parallel">
        <P>Research and Coding agents execute their tasks under the concurrency manager. The Critic reviews each output and requests refinements when needed.</P>
      </Step>
      <Step n={4} title="Synthesizer produces a final report">
        <P>Once all tasks are approved, the Synthesizer compiles key points, risks, and recommendations into a structured summary stored in memory.</P>
      </Step>
      <Callout icon="📌">Go to the <strong>Goals page</strong> for goal-specific sample prompts and a live task tree view.</Callout>
      <H3>Sample goal prompts</H3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          'Create a 6-week goal to launch a public REST API for our product.',
          'I want to reduce bundle size by 30% — plan it out.',
          'Set a goal to improve test coverage from 55% to 85% across core modules.',
          'Plan a goal to migrate our PostgreSQL schema to a multi-tenant model.',
        ].map((p) => <SamplePrompt key={p} text={p} />)}
      </div>
    </Section>

    {/* ── TASKS ── */}
    <Section title="✅ Tasks — Running background operations">
      <P>Tasks are discrete, queued operations: read a file, generate code, analyse a dataset. They run asynchronously so the UI stays responsive.</P>
      <H2>Task types</H2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        {[
          { type: 'read_file',        desc: 'Read text content from an uploaded file.' },
          { type: 'write_file',       desc: 'Write or overwrite a file in your upload sandbox.' },
          { type: 'append_file',      desc: 'Append text to an existing sandbox file.' },
          { type: 'generate_code',    desc: 'Generate code via LLM for a given context and language.' },
          { type: 'dataset_analysis', desc: 'Run statistical analysis on a CSV: row count, column types, top values.' },
        ].map(({ type, desc }) => (
          <div key={type} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 7, padding: '10px 12px' }}>
            <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#7c6af7', fontWeight: 700, marginBottom: 4 }}>{type}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{desc}</div>
          </div>
        ))}
      </div>
      <H3>Polling pattern</H3>
      <Step n={1} title="POST /api/v1/tasks — enqueue">
        <P>Send <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>{'{ "type": "...", "payload": {...} }'}</code>. You get back a task ID immediately.</P>
      </Step>
      <Step n={2} title="GET /api/v1/tasks/:id — poll">
        <P>Poll every few seconds until <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>status</code> is <strong>completed</strong> or <strong>failed</strong>. The result is in the <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>result</code> field.</P>
      </Step>
      <H3>Sample task prompts</H3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          'Read the file I just uploaded and give me a summary.',
          'Analyse my sales.csv — what are the top 5 revenue categories?',
          'Generate a TypeScript interface from the JSON schema I uploaded.',
          'What tasks are currently queued or running?',
        ].map((p) => <SamplePrompt key={p} text={p} />)}
      </div>
    </Section>

    {/* ── WORKSPACE ── */}
    <Section title="📁 Workspace — Files & Projects" defaultOpen={false}>
      <P>Upload files and organise them into Projects. Attach uploaded files to a project and reference their <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>upload_id</code> in task payloads.</P>
      <Step n={1} title="Upload a file"><P>Click 📎 in the chat, or use the Workspace page uploader. Allowed types: .txt .csv .json .pdf .docx .png .jpg .mp3 .mp4.</P></Step>
      <Step n={2} title="Create or select a project"><P>Group related uploads under a named Project. The project_id is auto-saved and used when creating tasks.</P></Step>
      <Step n={3} title="Reference in a task"><P>Use the upload_id in a task payload: <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>{'{"type":"read_file","payload":{"upload_id":"..."}}'}</code></P></Step>
      <H3>Sample workspace prompts</H3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          'Create a project called "Q3 Product Launch" and attach the brief I uploaded.',
          'List all files in the current project.',
          'What projects exist and when were they created?',
        ].map((p) => <SamplePrompt key={p} text={p} />)}
      </div>
    </Section>

    {/* ── TIPS ── */}
    <Section title="⚡ Tips & Best Practices" defaultOpen={false}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Callout icon="📝">Be specific with goals — include a timeframe, a measurable outcome, and the scope (e.g. "API layer only, not frontend").</Callout>
        <Callout icon="🔄">For complex goals, use the autonomous mode: start with "Plan and execute…" and let the agent loop run to completion.</Callout>
        <Callout icon="🛑">If a task fails, check the <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>error</code> field via GET /api/v1/tasks/:id and re-enqueue with corrected payload.</Callout>
        <Callout icon="📂">Attach a file before describing a complex task — having the content available as context dramatically improves output quality.</Callout>
      </div>
    </Section>
  </div>
);

export default HowToPage;
