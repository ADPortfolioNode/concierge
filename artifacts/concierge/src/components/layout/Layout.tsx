import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';

// ── nav group separator ───────────────────────────────────────────────────
const NavSep: React.FC = () => (
  <span className="nav-sep" aria-hidden="true" />
);

// ── Exponential backoff with full jitter (AWS/Google pattern) ──────────────
// delay = random(0, min(cap, base * 2^attempt))
const BACKOFF_BASE_MS  = 500;
const BACKOFF_CAP_MS   = 16_000;
const BACKOFF_MAX_TRIES = 8;
const FETCH_TIMEOUT_MS  = 5_000;

function backoffDelay(attempt: number): number {
  const ceiling = Math.min(BACKOFF_CAP_MS, BACKOFF_BASE_MS * 2 ** attempt);
  return Math.random() * ceiling;
}

async function fetchWithTimeout(url: string, timeoutMs = FETCH_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

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
  // attempt = which retry we're on (0-based); null = succeeded; BACKOFF_MAX_TRIES = exhausted
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  // increment this to re-trigger the startup effect (manual retry)
  const [retryKey, setRetryKey] = useState(0);

  const setStepStatus = (index: number, status: StepStatus) =>
    setSteps(prev => prev.map((s, i) => (i === index ? { ...s, status } : s)));

  useEffect(() => {
    let cancelled = false;

    // Reset state on each run (including manual retries)
    setFailed(false);
    setCountdown(null);
    setAttempt(0);
    setProgress(0);
    setSteps(INITIAL_STEPS);

    // Progress bar: eases toward 85% while waiting, jumps to 100% on success
    const progressTimer = setInterval(() => {
      setProgress(p => (p < 85 ? p + (85 - p) * 0.12 : p));
    }, 400);

    // ── exponential backoff loop ────────────────────────────────────────────
    const run = async () => {
      setStepStatus(0, 'loading');

      for (let i = 0; i < BACKOFF_MAX_TRIES; i++) {
        if (cancelled) return;
        setAttempt(i);

        try {
          const res = await fetchWithTimeout('/api/health');
          if (!cancelled && res.ok) {
            const data = await res.json() as { status?: string };
            if (data.status === 'ok') {
              if (cancelled) return;
              setStepStatus(0, 'done');

              // Step 1 — capabilities
              setStepStatus(1, 'loading');
              try {
                await fetchWithTimeout('/api/v1/capabilities');
                if (!cancelled) setStepStatus(1, 'done');
              } catch {
                if (!cancelled) setStepStatus(1, 'error');
              }

              // Step 2 — memory / messages
              if (cancelled) return;
              setStepStatus(2, 'loading');
              try {
                await fetchWithTimeout('/api/v1/concierge/messages');
                if (!cancelled) setStepStatus(2, 'done');
              } catch {
                if (!cancelled) setStepStatus(2, 'error');
              }

              // Step 3 — ready
              if (cancelled) return;
              setStepStatus(3, 'loading');
              setProgress(100);
              await new Promise(r => setTimeout(r, 350));
              if (!cancelled) {
                setStepStatus(3, 'done');
                await new Promise(r => setTimeout(r, 400));
                if (!cancelled) setIsReady(true);
              }
              return; // success — exit loop
            }
          }
        } catch {
          // timeout or network error — fall through to backoff
        }

        // Not the last attempt: back off with full jitter + live countdown
        if (i < BACKOFF_MAX_TRIES - 1 && !cancelled) {
          setStepStatus(0, 'error');
          const delay = backoffDelay(i);
          const endAt = Date.now() + delay;

          // tick the countdown label every 500 ms
          await new Promise<void>(resolve => {
            const tick = setInterval(() => {
              const remaining = Math.max(0, endAt - Date.now());
              if (!cancelled) setCountdown(Math.ceil(remaining / 1000));
              if (remaining <= 0) { clearInterval(tick); resolve(); }
            }, 500);
            setTimeout(() => { clearInterval(tick); resolve(); }, delay + 50);
          });

          if (!cancelled) {
            setCountdown(null);
            setStepStatus(0, 'loading');
          }
        }
      }

      // All retries exhausted
      if (!cancelled) {
        setStepStatus(0, 'error');
        setFailed(true);
      }
    };

    run();

    return () => {
      cancelled = true;
      clearInterval(progressTimer);
    };
  }, [retryKey]);

  if (!isReady) {
    const isFailed = failed;
    const showCountdown = !isFailed && countdown !== null && countdown > 0;
    const retryLabel = isFailed
      ? 'Could not reach the API server'
      : showCountdown
        ? `Retrying in ${countdown}s… (attempt ${attempt + 1} of ${BACKOFF_MAX_TRIES})`
        : attempt > 0
          ? `Attempt ${attempt + 1} of ${BACKOFF_MAX_TRIES}…`
          : null;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0f172a', color: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 36 }}>
          <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" style={{ height: 48 }} fetchPriority="high" />
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em' }}>Concierge</h1>
        </div>

        {/* progress bar */}
        <div style={{ width: 300, background: 'rgba(255,255,255,0.08)', borderRadius: 8, overflow: 'hidden', height: 6, marginBottom: 28 }}>
          <div style={{ width: `${isFailed ? progress : progress}%`, background: isFailed ? 'rgba(239,68,68,0.6)' : 'linear-gradient(90deg, #6d56f5, #a78bfa)', height: '100%', transition: 'width 0.4s ease-out', borderRadius: 8 }} />
        </div>

        {/* step list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 260 }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: step.status === 'pending' ? 0.3 : 1, transition: 'opacity 0.3s' }}>
              <StepIcon status={step.status} />
              <span style={{ fontSize: 13, color: step.status === 'done' ? '#e2e8f0' : step.status === 'error' ? '#fca5a5' : '#94a3b8', transition: 'color 0.3s' }}>
                {step.label}
              </span>
            </div>
          ))}
        </div>

        {/* retry / countdown hint */}
        {retryLabel && (
          <p style={{ marginTop: 20, fontSize: 12, color: isFailed ? '#fca5a5' : '#64748b', textAlign: 'center', maxWidth: 260 }}>
            {retryLabel}
          </p>
        )}

        {/* manual retry button — shown only after all attempts are exhausted */}
        {isFailed && (
          <button
            onClick={() => setRetryKey(k => k + 1)}
            style={{ marginTop: 16, padding: '8px 20px', borderRadius: 6, border: '1px solid rgba(167,139,250,0.4)', background: 'transparent', color: '#a78bfa', fontSize: 13, cursor: 'pointer', transition: 'background 0.2s' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(109,86,245,0.15)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            Retry connection
          </button>
        )}
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