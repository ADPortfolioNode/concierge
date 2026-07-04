import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import SamplePrompt from '@/components/primitives/SamplePrompt';
import TimelineHero from '@/components/TimelineHero';
import { useAppStore } from '@/state/appStore';

const QUICK_PROMPTS = [
  'What can you help me with?',
  'Generate a simple logo for Concierge',
  'Show me what tasks are running',
  'Summarise my last project context',
];

const HomePage: React.FC = () => {
  const taskThreadId = useAppStore((s) => s.taskThreadId);
  const timelinePlan = useAppStore((s) => s.timelinePlan);
  const hasTasks = useMemo(() => {
    const tasks = timelinePlan?.tasks ?? timelinePlan?.plan?.tasks;
    return Array.isArray(tasks) && tasks.length > 0;
  }, [timelinePlan]);
  const showTimeline = !!taskThreadId || hasTasks;

  return (
    <div className="home-page page-content" style={{ maxWidth: 900, margin: '0 auto', padding: '24px 20px' }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28, fontWeight: 800, color: '#0F172A' }}>Concierge</h1>
      <p style={{ margin: '0 0 24px', fontSize: 15, color: '#64748B', lineHeight: 1.6, maxWidth: 520 }}>
        Orchestrator ready — chat on the right to plan work, generate media, or ask questions.
        Track progress on{' '}
        <Link to="/tasks" style={{ color: '#2563EB', fontWeight: 600 }}>Tasks</Link>
        {' '}and view output on{' '}
        <Link to="/media" style={{ color: '#2563EB', fontWeight: 600 }}>Media</Link>.
      </p>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Try asking
        </h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {QUICK_PROMPTS.map((p) => (
            <SamplePrompt key={p} text={p} variant="chip" />
          ))}
        </div>
      </section>

      {showTimeline && (
        <section style={{ marginBottom: 24, padding: 16, background: '#F8FAFF', borderRadius: 12, border: '1px solid #DBEAFE' }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 700, color: '#0F172A' }}>Active workflow</h2>
          <TimelineHero />
        </section>
      )}
    </div>
  );
};

export default HomePage;