import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';

// ── nav group separator ───────────────────────────────────────────────────
const NavSep: React.FC = () => (
  <span className="nav-sep" aria-hidden="true" />
);

type StepStatus = 'pending' | 'loading' | 'done' | 'error';

interface StartupStep {
  label: string;
  status: StepStatus;
}

const INITIAL_STEPS: StartupStep[] = [
  { label: 'Connecting to API', status: 'pending' },
  { label: 'Loading capabilities', status: 'pending' },
  { label: 'Initialising memory', status: 'pending' },
  { label: 'Ready', status: 'pending' },
];

const StepIcon: React.FC<{ status: StepStatus }> = ({ status }) => {
  if (status === 'done') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
        <circle cx="8" cy="8" r="8" fill="#6d56f5" />
        <path d="M4.5 8l2.5 2.5 4.5-5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === 'error') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
        <circle cx="8" cy="8" r="8" fill="#ef4444" opacity="0.8" />
        <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  if (status === 'loading') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, animation: 'spin 1s linear infinite' }}>
        <circle cx="8" cy="8" r="6" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
        <path d="M8 2a6 6 0 0 1 6 6" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="6" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
    </svg>
  );
};

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isReady, setIsReady] = useState(false);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StartupStep[]>(INITIAL_STEPS);

  const setStepStatus = (index: number, status: StepStatus) => {
    setSteps(prev => prev.map((s, i) => i === index ? { ...s, status } : s));
  };

  useEffect(() => {
    // Animate progress bar independently so it always feels alive
    const timer = setInterval(() => {
      setProgress(p => (p < 85 ? p + (85 - p) * 0.12 : p));
    }, 400);

    // Step 0: connecting to API
    setStepStatus(0, 'loading');

    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json() as { status?: string; messages?: unknown[]; version?: string };
          if (data.status === 'ok') {
            setStepStatus(0, 'done');

            // Step 1: capabilities
            setStepStatus(1, 'loading');
            try {
              await fetch('/api/v1/capabilities');
              setStepStatus(1, 'done');
            } catch {
              setStepStatus(1, 'error');
            }

            // Step 2: memory / messages
            setStepStatus(2, 'loading');
            try {
              await fetch('/api/v1/concierge/messages');
              setStepStatus(2, 'done');
            } catch {
              setStepStatus(2, 'error');
            }

            // Step 3: done
            setStepStatus(3, 'loading');
            setProgress(100);
            setTimeout(() => {
              setStepStatus(3, 'done');
              setTimeout(() => setIsReady(true), 400);
            }, 300);

            return true;
          }
        }
      } catch {
        // backend not yet up — stay on step 0 loading
      }
      return false;
    };

    const pollInterval = setInterval(async () => {
      const ready = await checkHealth();
      if (ready) clearInterval(pollInterval);
    }, 2000);

    checkHealth().then(ready => {
      if (ready) clearInterval(pollInterval);
    });

    return () => {
      clearInterval(timer);
      clearInterval(pollInterval);
    };
  }, []);

  if (!isReady) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0f172a', color: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 36 }}>
          <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" style={{ height: 48 }} fetchPriority="high" />
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em' }}>Concierge</h1>
        </div>

        {/* progress bar */}
        <div style={{ width: 300, background: 'rgba(255,255,255,0.08)', borderRadius: 8, overflow: 'hidden', height: 6, marginBottom: 28 }}>
          <div style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #6d56f5, #a78bfa)', height: '100%', transition: 'width 0.4s ease-out', borderRadius: 8 }} />
        </div>

        {/* step list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 220 }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: step.status === 'pending' ? 0.35 : 1, transition: 'opacity 0.3s' }}>
              <StepIcon status={step.status} />
              <span style={{ fontSize: 13, color: step.status === 'done' ? '#e2e8f0' : step.status === 'error' ? '#fca5a5' : '#94a3b8', transition: 'color 0.3s' }}>
                {step.label}
              </span>
              {step.status === 'error' && (
                <span style={{ fontSize: 11, color: '#fca5a5', marginLeft: 'auto' }}>retrying</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // responsive layout styles handled via CSS grid in index.css
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <NavLink to="/" end style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
            <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" className="brand-logo" style={{ height: 26 }} fetchPriority="high" />
              <span style={{ color: '#f8fafc', fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em' }}>Concierge</span>
            </NavLink>
          </div>

          {/* Grouped navigation: Achieve | Execute | Resources */}
          <nav className="header-nav" aria-label="Main navigation">
            {/* hub */}
            <NavLink to="/" end title="Dashboard">Home</NavLink>

            <NavSep />

            {/* achieve / plan */}
            <NavLink to="/goals"    title="Set and track your goals">Goals</NavLink>
            <NavLink to="/strategy" title="Strategic planning & frameworks">Strategy</NavLink>

            <NavSep />

            {/* execute / do */}
            <NavLink to="/tasks"     title="Automate and run background tasks">Tasks</NavLink>
            <NavLink to="/workspace" title="Files, projects and context">Workspace</NavLink>
            <NavLink to="/media" title="View multimedia output">Media</NavLink>

            <NavSep />

            {/* learn */}
            <NavLink to="/howto"        title="How-to guide and tutorials">Guide</NavLink>
            <NavLink to="/capabilities" title="Registered plugins and integrations">Integrations</NavLink>
          </nav>
        </div>
      </header>

      <main className="app-main">{children}</main>

      <aside className="app-chat" role="complementary" aria-label="AI Concierge chat">
        <ChatContainer />
      </aside>

      {/* global error banner — position:fixed, bottom of viewport */}
      <ErrorBanner />
    </div>
  );
};

export default Layout;