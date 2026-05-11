import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import SamplePrompt from '@/components/primitives/SamplePrompt';
import TimelineHero from '@/components/TimelineHero';
import SacredTimelineHero from '@/components/SacredTimelineHero';
import PageSection from '@/components/PageSection';
import { useAppStore } from '@/state/appStore';

const BUSINESSWOMAN_PHOTO =
  'https://images.presentationgo.com/2025/04/businesswoman-working-laptop-office.jpg';

const TEAM_PHOTO2 =
  'https://thumbs.dreamstime.com/b/young-smiling-business-people-working-laptops-group-coworkers-sitting-together-table-modern-office-teamwork-124959385.jpg';

// ── featured workflow definitions ─────────────────────────────────────────
const USE_CASES = [
  {
    icon: '📷',
    title: 'Photo Review Workflow',
    tagline: 'Summarize, tag, and clean up photos',
    description:
      'Use image-based tasks to review uploaded photos, generate captions and tags, flag low-quality shots, and produce a clean, organized output set.',
    color: '#7C3AED',
    link: '/tasks',
    cta: 'Open Tasks →',
    prompts: [
      'Summarize and tag the photos I uploaded from the team event.',
      'Review these product photos and flag any that look low quality.',
      'Rename my uploaded photo batch by subject matter and write captions.',
    ],
  },
  {
    icon: '📄',
    title: 'Report Generation',
    tagline: 'From raw uploads to polished deliverables',
    description:
      'Extract insights from documents, spreadsheets, and uploads. Concierge creates polished summaries, executive briefs, and final deliverables ready to share.',
    color: '#0891B2',
    link: '/tasks',
    cta: 'Open Tasks →',
    prompts: [
      'Extract key insights from the PDF I uploaded and write a polished summary.',
      'Turn my uploaded data into an executive report with recommendations.',
      'Generate a final deliverable from the project notes I shared.',
    ],
  },
  {
    icon: '📈',
    title: 'Data-Driven Decisions',
    tagline: 'Turn numbers into action',
    description:
      'Feed Concierge your spreadsheets and logs. It analyses patterns, surfaces anomalies, and returns prioritised, actionable business recommendations.',
    color: '#059669',
    link: '/tasks',
    cta: 'Open Tasks →',
    prompts: [
      'Analyse my spreadsheet and give me actionable business recommendations.',
      'Look at the logs I uploaded and find patterns worth acting on.',
      'What should we prioritise based on the data in this CSV?',
    ],
  },
];

// ── outcome card ──────────────────────────────────────────────────────────
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
      background: '#FFFFFF',
      border: `1px solid ${color}22`,
      borderRadius: 16,
      padding: '22px 22px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      transition: 'border-color 0.2s, box-shadow 0.2s, transform 0.2s',
      boxShadow: '0 2px 8px rgba(37,99,235,0.06)',
    }}
    onMouseEnter={(e) => {
      const el = e.currentTarget as HTMLDivElement;
      el.style.borderColor = `${color}44`;
      el.style.boxShadow = `0 8px 28px ${color}18`;
      el.style.transform = 'translateY(-2px)';
    }}
    onMouseLeave={(e) => {
      const el = e.currentTarget as HTMLDivElement;
      el.style.borderColor = `${color}22`;
      el.style.boxShadow = '0 2px 8px rgba(37,99,235,0.06)';
      el.style.transform = 'translateY(0)';
    }}
  >
    {/* header row */}
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
      <span
        style={{
          fontSize: 26,
          lineHeight: 1,
          background: `${color}12`,
          border: `1px solid ${color}22`,
          borderRadius: 10,
          padding: '9px 11px',
          flexShrink: 0,
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#0F172A', marginBottom: 2 }}>{title}</div>
        <div style={{ fontSize: 11, color: color, fontWeight: 600 }}>{tagline}</div>
      </div>
    </div>

    <p style={{ fontSize: 13, color: '#64748B', margin: 0, lineHeight: 1.65 }}>
      {description}
    </p>

    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {prompts.map((p) => (
        <SamplePrompt key={p} text={p} variant="chip" />
      ))}
    </div>

    <Link
      to={link}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 13,
        fontWeight: 700,
        color: color,
        textDecoration: 'none',
        marginTop: 2,
        transition: 'opacity 0.15s',
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.opacity = '0.7'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.opacity = '1'; }}
    >
      {cta}
    </Link>
  </div>
);

// ── photo banner ──────────────────────────────────────────────────────────
const PhotoBanner: React.FC = () => (
  <div
    style={{
      borderRadius: 20,
      overflow: 'hidden',
      marginBottom: 36,
      position: 'relative',
      border: '1px solid #DBEAFE',
      boxShadow: '0 8px 32px rgba(37,99,235,0.1)',
    }}
  >
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 180 }}>
      {/* left: text */}
      <div
        style={{
          background: 'linear-gradient(135deg, #2563EB 0%, #0EA5E9 100%)',
          padding: '28px 28px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 10,
        }}
      >
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.16em', color: 'rgba(255,255,255,0.7)' }}>
          AI-Powered Productivity
        </div>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 900, color: '#FFFFFF', lineHeight: 1.15, letterSpacing: '-0.02em' }}>
          Work smarter,<br />achieve more
        </h2>
        <p style={{ margin: 0, fontSize: 13, color: 'rgba(255,255,255,0.78)', lineHeight: 1.6, maxWidth: 280 }}>
          Concierge orchestrates complex goals into structured plans so your team stays focused on what matters.
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          {['Goals', 'Strategy', 'Tasks', 'Workspace'].map((label) => (
            <span
              key={label}
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: 'rgba(255,255,255,0.9)',
                background: 'rgba(255,255,255,0.18)',
                borderRadius: 999,
                padding: '3px 10px',
                border: '1px solid rgba(255,255,255,0.25)',
              }}
            >
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* right: real photo */}
      <div style={{ position: 'relative', overflow: 'hidden', maxHeight: 240 }}>
        <img
          src={BUSINESSWOMAN_PHOTO}
          alt="Professional using AI assistant"
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          loading="lazy"
          onError={(e) => {
            const el = e.currentTarget as HTMLImageElement;
            el.style.display = 'none';
            // try fallback
            const fallback = document.createElement('img');
            fallback.src = TEAM_PHOTO2;
            fallback.style.cssText = el.style.cssText;
            el.parentElement?.appendChild(fallback);
          }}
        />
        {/* subtle blue overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to right, rgba(37,99,235,0.12) 0%, transparent 60%)',
            pointerEvents: 'none',
          }}
        />
      </div>
    </div>
  </div>
);

// ── main page ─────────────────────────────────────────────────────────────
const HomePage: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const hasTasks = useMemo(() => {
    const tasks = timelinePlan?.tasks ?? timelinePlan?.plan?.tasks;
    return Array.isArray(tasks) && tasks.length > 0;
  }, [timelinePlan]);
  const showTimeline = !!taskThreadId || hasTasks;

  return (
    <div className="home-page">
      {/* sacred timeline hero */}
      <SacredTimelineHero />

      {/* photo banner */}
      <PhotoBanner />

      {showTimeline && (
        <div className="home-timeline-card">
          <div className="home-timeline-header">
            <div>
              <div className="home-timeline-label">Live Timeline</div>
              <h2 className="home-timeline-title">Active agent thread — task graph &amp; progress</h2>
              <p className="home-timeline-copy">
                Watch the Sacred Timeline orchestrate tasks in real time. Each node below represents a step
                spawned by the Planner, streamed live via WebSocket as it runs.
              </p>
            </div>
          </div>
          <TimelineHero />
        </div>
      )}

      <PageSection title="Quick actions">
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
      </PageSection>

      <PageSection title="Featured workflows">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 16,
          }}
        >
          {USE_CASES.map((uc) => (
            <OutcomeCard key={uc.title} {...uc} />
          ))}
        </div>
      </PageSection>

      <PageSection title="More resources">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
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
                padding: '12px 20px',
                borderRadius: 12,
                background: '#FFFFFF',
                border: '1px solid #DBEAFE',
                color: '#0F172A',
                textDecoration: 'none',
                fontSize: 13,
                fontWeight: 600,
                gap: 3,
                transition: 'border-color 0.15s, box-shadow 0.15s, transform 0.15s',
                boxShadow: '0 1px 4px rgba(37,99,235,0.06)',
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.borderColor = '#93C5FD';
                el.style.boxShadow = '0 6px 20px rgba(37,99,235,0.12)';
                el.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.borderColor = '#DBEAFE';
                el.style.boxShadow = '0 1px 4px rgba(37,99,235,0.06)';
                el.style.transform = 'translateY(0)';
              }}
            >
              <span>{label}</span>
              <span style={{ fontSize: 11, color: '#94A3B8', fontWeight: 400 }}>{desc}</span>
            </Link>
          ))}
        </div>
      </PageSection>
    </div>
  );
};

export default HomePage;
