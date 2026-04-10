import React from 'react';
import { Link } from 'react-router-dom';
import SamplePrompt from '@/components/primitives/SamplePrompt';

// ── use-case outcome definitions ─────────────────────────────────────────
const USE_CASES = [
  {
    icon: '🎯',
    title: 'Achieve Your Goals',
    tagline: 'Turn ambitions into results',
    description:
      'Set high-level outcomes, let Concierge break them into prioritised tasks, and track progress automatically.',
    color: '#7c6af7',
    link: '/goals',
    cta: 'Open Goals →',
    prompts: [
      'Create a 4-week goal to migrate our REST API to GraphQL.',
      'I want to reduce page load time by 40% — plan it out.',
      'Set weekly goals for improving test coverage from 60% to 90%.',
    ],
  },
  {
    icon: '⚡',
    title: 'Automate Your Work',
    tagline: 'Execute tasks without lifting a finger',
    description:
      'Run background tasks asynchronously: analyse files, generate code, process datasets, and get results delivered.',
    color: '#059669',
    link: '/tasks',
    cta: 'Open Tasks →',
    prompts: [
      'Analyse the CSV I uploaded and summarise the key trends.',
      'Generate a Python script to parse JSON logs and extract error counts.',
      'Read my uploaded spec and list all missing edge cases.',
    ],
  },
  {
    icon: '🗺️',
    title: 'Plan Your Strategy',
    tagline: 'Think clearly, decide confidently',
    description:
      'Apply OKRs, SWOT analysis, RICE scoring, and roadmapping frameworks. Let Concierge be your strategic thinking partner.',
    color: '#0891b2',
    link: '/strategy',
    cta: 'Open Strategy →',
    prompts: [
      'Write 3 OKRs for our product team for Q3 2026.',
      'Run a SWOT analysis for a developer-tools startup.',
      'Build a 6-month product roadmap for a data-analytics platform.',
    ],
  },
  {
    icon: '📁',
    title: 'Manage Your Workspace',
    tagline: 'All your files and context in one place',
    description:
      'Upload documents, images, CSVs, and PDFs. Attach them to projects and reference them in any conversation.',
    color: '#d97706',
    link: '/workspace',
    cta: 'Open Workspace →',
    prompts: [
      "I've uploaded a PDF spec — summarise the authentication requirements.",
      'Attach the financial model CSV to the Q2 Planning project.',
      'Transcribe the audio file I uploaded and summarise it.',
    ],
  },
];

// ── section heading ───────────────────────────────────────────────────────
const SectionHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2
    style={{
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.12em',
      color: 'rgba(255,255,255,0.3)',
      margin: '0 0 16px',
      paddingBottom: 8,
      borderBottom: '1px solid rgba(255,255,255,0.05)',
    }}
  >
    {children}
  </h2>
);

// ── use-case outcome card ─────────────────────────────────────────────────
const OutcomeCard: React.FC<(typeof USE_CASES)[0]> = ({
  icon,
  title,
  tagline,
  description,
  color,
  link,
  cta,
  prompts,
}) => (
  <div
    style={{
      background: 'rgba(255,255,255,0.02)',
      border: `1px solid ${color}28`,
      borderRadius: 12,
      padding: '24px 24px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      transition: 'border-color 0.2s',
    }}
    onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = `${color}55`; }}
    onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = `${color}28`; }}
  >
    {/* header row */}
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
      <span
        style={{
          fontSize: 28,
          lineHeight: 1,
          background: `${color}18`,
          border: `1px solid ${color}30`,
          borderRadius: 10,
          padding: '10px 12px',
          flexShrink: 0,
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: '#e2e8f0', marginBottom: 2 }}>{title}</div>
        <div style={{ fontSize: 12, color: color, fontWeight: 600, opacity: 0.9 }}>{tagline}</div>
      </div>
    </div>

    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', margin: 0, lineHeight: 1.65 }}>
      {description}
    </p>

    {/* sample prompts */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {prompts.map((p) => (
        <SamplePrompt key={p} text={p} variant="chip" />
      ))}
    </div>

    {/* CTA link */}
    <Link
      to={link}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 13,
        fontWeight: 600,
        color: color,
        textDecoration: 'none',
        marginTop: 2,
        opacity: 0.85,
        transition: 'opacity 0.15s',
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.opacity = '1'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.opacity = '0.85'; }}
    >
      {cta}
    </Link>
  </div>
);

// ── main page ─────────────────────────────────────────────────────────────
const VISUAL_CARDS = [
  {
    src: '/workflow-collaboration.svg',
    alt: 'Collaboration workflow illustration',
    label: 'Collaboration',
    title: 'Work together on AI-driven planning',
  },
  {
    src: '/workflow-insights.svg',
    alt: 'Insights workflow illustration',
    label: 'Insights',
    title: 'Monitor progress with clear metrics',
  },
  {
    src: '/workflow-design.svg',
    alt: 'Design workflow illustration',
    label: 'Design',
    title: 'Visualise strategy, tasks, and outcomes',
  },
];

const HomePage: React.FC = () => (
  <div
    style={{
      padding: '32px 28px 56px',
      maxWidth: 1060,
      margin: '0 auto',
      color: '#e2e8f0',
    }}
  >
    {/* hero */}
    <div
      style={{
        marginBottom: 40,
        display: 'grid',
        gridTemplateColumns: '1.2fr 0.9fr',
        gap: 24,
        alignItems: 'center',
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em', color: '#7c6af7', background: 'rgba(124,106,247,0.12)', border: '1px solid rgba(124,106,247,0.25)', borderRadius: 99, padding: '3px 10px' }}>
            AI Ops Concierge
          </span>
        </div>
        <h1 style={{ fontSize: 38, fontWeight: 800, margin: '0 0 14px', letterSpacing: '-0.02em', lineHeight: 1.08 }}>
          Build smarter workflows,
          <br />
          <span style={{ color: '#7c6af7' }}>see results visually.</span>
        </h1>
        <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.7)', margin: 0, maxWidth: 600, lineHeight: 1.75 }}>
          Jump into the chat or browse the visual workspace. Use AI to plan, execute,
          and monitor tasks, then surface photo-driven insights and media outputs.
        </p>
        <div style={{ marginTop: 24, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <SamplePrompt text="Show me my current roadmap" variant="chip" />
          <SamplePrompt text="Create a visual status update" variant="chip" />
          <SamplePrompt text="Generate a media summary" variant="chip" />
        </div>
      </div>

      <div
        style={{
          position: 'relative',
          minHeight: 360,
          borderRadius: 24,
          overflow: 'hidden',
          boxShadow: '0 40px 90px rgba(15, 23, 42, 0.35)',
          background: 'linear-gradient(135deg, rgba(18,18,36,0.92) 0%, rgba(30,16,56,0.98) 100%)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at 30% 20%, rgba(124,106,247,0.25), transparent 28%), radial-gradient(circle at 75% 15%, rgba(14,165,233,0.18), transparent 22%), radial-gradient(circle at 50% 80%, rgba(34,197,94,0.18), transparent 26%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backdropFilter: 'blur(14px)',
            mixBlendMode: 'screen',
          }}
        />

        <div style={{ position: 'relative', height: '100%', padding: 22, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {VISUAL_CARDS.slice(0, 2).map((card) => (
            <div key={card.label} style={{ borderRadius: 18, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(15, 23, 42, 0.9)' }}>
              <img src={card.src} alt={card.alt} style={{ width: '100%', height: 168, objectFit: 'cover' }} />
              <div style={{ padding: '14px 12px' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#c4b8ff', marginBottom: 6 }}>{card.label}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', lineHeight: 1.3 }}>{card.title}</div>
              </div>
            </div>
          ))}
          <div style={{ borderRadius: 18, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(15, 23, 42, 0.9)', display: 'grid', alignContent: 'space-between', padding: 18 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#7dd3fc', marginBottom: 10 }}>Visual summary</div>
              <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#ffffff', lineHeight: 1.2 }}>Photos, charts, and media previews</h2>
              <p style={{ margin: '14px 0 0', fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.7 }}>
                Browse your content library and preview image-based deliverables without leaving the dashboard.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 10 }}>
              {VISUAL_CARDS.slice(2).map((card) => (
                <img key={card.label} src={card.src} alt={card.alt} style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: 12 }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* quick-start chips */}
    <div style={{ marginBottom: 40 }}>
      <SectionHeading>Quick actions</SectionHeading>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {[
          'What can you help me with?',
          'Show me what tasks are running.',
          'Create a 2-week sprint plan for a new feature.',
          'Summarise my last project context.',
          'Help me prioritise my backlog.',
        ].map((p) => (
          <SamplePrompt key={p} text={p} variant="chip" />
        ))}
      </div>
    </div>

    {/* use-case outcome cards */}
    <div style={{ marginBottom: 40 }}>
      <SectionHeading>Choose your outcome</SectionHeading>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 16,
        }}
      >
        {USE_CASES.map((uc) => (
          <OutcomeCard key={uc.title} {...uc} />
        ))}
      </div>
    </div>

    {/* secondary links */}
    <div>
      <SectionHeading>More resources</SectionHeading>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {[
          { to: '/howto',        label: '📖 How-To Guide',    desc: 'Learn core workflows' },
          { to: '/capabilities', label: '🔌 Integrations',    desc: 'Browse plugins & tools' },
        ].map(({ to, label, desc }) => (
          <Link
            key={to}
            to={to}
            style={{
              display: 'inline-flex',
              flexDirection: 'column',
              padding: '10px 18px',
              borderRadius: 9,
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#d4d0ff',
              textDecoration: 'none',
              fontSize: 13,
              fontWeight: 600,
              gap: 2,
              transition: 'border-color 0.15s, background 0.15s',
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLAnchorElement;
              el.style.borderColor = 'rgba(124,106,247,0.4)';
              el.style.background = 'rgba(124,106,247,0.08)';
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLAnchorElement;
              el.style.borderColor = 'rgba(255,255,255,0.08)';
              el.style.background = 'rgba(255,255,255,0.03)';
            }}
          >
            <span>{label}</span>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontWeight: 400 }}>{desc}</span>
          </Link>
        ))}
      </div>
    </div>
  </div>
);

export default HomePage;
