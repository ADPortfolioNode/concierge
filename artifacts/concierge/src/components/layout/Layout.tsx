import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';
<<<<<<< HEAD
import { makeApiUrl } from '@/config/activeServer';
=======
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

// ── nav group separator ───────────────────────────────────────────────────
const NavSep: React.FC = () => (
  <span className="nav-sep" aria-hidden="true" />
);

// ── mobile nav separator ──────────────────────────────────────────────────
const MobileNavSep: React.FC = () => (
  <div className="mobile-nav-sep" aria-hidden="true" />
);

// ── hamburger icon (animates to X when open) ──────────────────────────────
const HamburgerIcon: React.FC<{ open: boolean }> = ({ open }) => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
    {open ? (
      <>
        <line x1="3" y1="3" x2="15" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="15" y1="3" x2="3" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      </>
    ) : (
      <>
        <line x1="2" y1="5" x2="16" y2="5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="2" y1="9" x2="16" y2="9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="2" y1="13" x2="16" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      </>
    )}
  </svg>
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
        <circle cx="8" cy="8" r="6" stroke="#BFDBFE" strokeWidth="2" />
        <path d="M8 2a6 6 0 0 1 6 6" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="6" stroke="#DBEAFE" strokeWidth="2" />
    </svg>
  );
};

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isReady, setIsReady] = useState(false);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StartupStep[]>(INITIAL_STEPS);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
<<<<<<< HEAD
  const [chatOpen, setChatOpen] = useState(true);
=======
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
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
<<<<<<< HEAD
          // Use the documented ready endpoint (supports /api prefix via alias)
          const healthUrl = makeApiUrl('/api/health/ready');
          const res = await fetchWithTimeout(healthUrl);
          if (!cancelled) {
            const data = await res.json().catch(() => ({})) as { status?: string };
            const ok = res.ok || data.status === 'ok';
            if (ok) {
              setStepStatus(0, 'done');

              // best-effort secondary checks (non-blocking)
              setStepStatus(1, 'loading');
              fetchWithTimeout(makeApiUrl('/api/v1/capabilities')).then(() => setStepStatus(1, 'done')).catch(() => setStepStatus(1, 'error'));

              setStepStatus(2, 'loading');
              fetchWithTimeout(makeApiUrl('/api/v1/concierge/conversation')).then(() => setStepStatus(2, 'done')).catch(() => setStepStatus(2, 'error'));

              setStepStatus(3, 'loading');
              setProgress(100);
              await new Promise(r => setTimeout(r, 250));
              if (!cancelled) {
                setStepStatus(3, 'done');
                await new Promise(r => setTimeout(r, 200));
                if (!cancelled) setIsReady(true);
              }
              return;
            }
          }
        } catch {
          // will retry
        }

        // backoff with countdown for remaining attempts
=======
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
                await fetchWithTimeout('/api/v1/concierge/conversation');
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
        if (i < BACKOFF_MAX_TRIES - 1 && !cancelled) {
          setStepStatus(0, 'error');
          const delay = backoffDelay(i);
          const endAt = Date.now() + delay;

<<<<<<< HEAD
=======
          // tick the countdown label every 500 ms
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
          await new Promise<void>(resolve => {
            const tick = setInterval(() => {
              const remaining = Math.max(0, endAt - Date.now());
              if (!cancelled) setCountdown(Math.ceil(remaining / 1000));
              if (remaining <= 0) { clearInterval(tick); resolve(); }
<<<<<<< HEAD
            }, 400);
            setTimeout(() => { clearInterval(tick); resolve(); }, delay + 30);
=======
            }, 500);
            setTimeout(() => { clearInterval(tick); resolve(); }, delay + 50);
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
          });

          if (!cancelled) {
            setCountdown(null);
            setStepStatus(0, 'loading');
          }
        }
      }

<<<<<<< HEAD
=======
      // All retries exhausted
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
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

<<<<<<< HEAD
  // UX improvement: never fully block the app shell behind startup.
  // Render header + main content + chat immediately.
  // Show a friendly top status banner only while connecting on first load.
  const showBlockingLoader = !isReady && attempt === 0 && !failed;
  const isConnecting = !isReady && !failed;
  const showConnectionBanner = !isReady && (failed || attempt > 0);
=======
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
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'linear-gradient(135deg, #F0F8FF 0%, #EFF6FF 100%)', color: '#0F172A', fontFamily: 'system-ui, sans-serif' }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 36 }}>
          <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" style={{ height: 48 }} fetchPriority="high" />
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em', color: '#0F172A' }}>Concierge</h1>
        </div>

        {/* progress bar */}
        <div style={{ width: 300, background: '#DBEAFE', borderRadius: 8, overflow: 'hidden', height: 6, marginBottom: 28 }}>
          <div style={{ width: `${isFailed ? progress : progress}%`, background: isFailed ? '#EF4444' : 'linear-gradient(90deg, #2563EB, #38BDF8)', height: '100%', transition: 'width 0.4s ease-out', borderRadius: 8 }} />
        </div>

        {/* step list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 260 }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: step.status === 'pending' ? 0.3 : 1, transition: 'opacity 0.3s' }}>
              <StepIcon status={step.status} />
              <span style={{ fontSize: 13, color: step.status === 'done' ? '#0F172A' : step.status === 'error' ? '#B91C1C' : '#64748B', transition: 'color 0.3s' }}>
                {step.label}
              </span>
            </div>
          ))}
        </div>

        {/* retry / countdown hint */}
        {retryLabel && (
          <p style={{ marginTop: 20, fontSize: 12, color: isFailed ? '#B91C1C' : '#64748B', textAlign: 'center', maxWidth: 260 }}>
            {retryLabel}
          </p>
        )}

        {/* manual retry button — shown only after all attempts are exhausted */}
        {isFailed && (
          <button
            onClick={() => setRetryKey(k => k + 1)}
            style={{ marginTop: 16, padding: '8px 20px', borderRadius: 6, border: '1px solid #BFDBFE', background: '#FFFFFF', color: '#2563EB', fontSize: 13, cursor: 'pointer', transition: 'background 0.2s', fontWeight: 600 }}
            onMouseEnter={e => (e.currentTarget.style.background = '#EFF6FF')}
            onMouseLeave={e => (e.currentTarget.style.background = '#FFFFFF')}
          >
            Retry connection
          </button>
        )}
      </div>
    );
  }
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

  const closeNav = () => setMobileNavOpen(false);

  // responsive layout styles handled via CSS grid in index.css
  return (
    <div className="app-container">
<<<<<<< HEAD
      <style>{`@media (max-width:959px){.chat-toggle-btn{display:none!important}}`}</style>
=======
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
      <header className="app-header" style={{ position: 'relative' }}>
        <div className="header-inner">
          <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <NavLink to="/" end onClick={closeNav} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
              <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" className="brand-logo" style={{ height: 26 }} fetchPriority="high" />
              <span style={{ color: '#0F172A', fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em' }}>Concierge</span>
            </NavLink>
          </div>

          {/* Desktop navigation */}
          <nav className="header-nav" aria-label="Main navigation">
            <NavLink to="/" end title="Dashboard">Home</NavLink>
            <NavSep />
            <NavLink to="/goals"        title="Set and track your goals">Goals</NavLink>
            <NavLink to="/strategy"     title="Strategic planning & frameworks">Strategy</NavLink>
            <NavSep />
            <NavLink to="/tasks"        title="Automate and run background tasks">Tasks</NavLink>
            <NavLink to="/workspace"    title="Files, projects and context">Workspace</NavLink>
            <NavLink to="/media"        title="View multimedia output">Media</NavLink>
            <NavSep />
            <NavLink to="/howto"        title="How-to guide and tutorials">Guide</NavLink>
            <NavLink to="/capabilities" title="Registered plugins and integrations">Integrations</NavLink>
          </nav>

          {/* Hamburger — mobile/tablet only */}
          <button
            className="hamburger-btn"
            aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(o => !o)}
          >
            <HamburgerIcon open={mobileNavOpen} />
          </button>
<<<<<<< HEAD

          {/* Desktop chat toggle for focus / more workspace space (visible >=960px) */}
          <button
            onClick={() => setChatOpen(o => !o)}
            title={chatOpen ? 'Hide chat sidebar' : 'Show chat sidebar'}
            style={{ fontSize: 12, padding: '4px 10px', border: '1px solid #BFDBFE', borderRadius: 6, background: 'white', cursor: 'pointer', marginLeft: 6, display: 'inline-flex', alignItems: 'center' }}
            className="chat-toggle-btn"
          >
            {chatOpen ? '⤫ Chat' : 'Chat ▸'}
          </button>
=======
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
        </div>

        {/* Mobile/tablet drawer */}
        {mobileNavOpen && (
          <nav className="mobile-nav" aria-label="Mobile navigation">
            <NavLink to="/" end onClick={closeNav}>Home</NavLink>
            <MobileNavSep />
            <NavLink to="/goals"        onClick={closeNav}>Goals</NavLink>
            <NavLink to="/strategy"     onClick={closeNav}>Strategy</NavLink>
            <MobileNavSep />
            <NavLink to="/tasks"        onClick={closeNav}>Tasks</NavLink>
            <NavLink to="/workspace"    onClick={closeNav}>Workspace</NavLink>
            <NavLink to="/media"        onClick={closeNav}>Media</NavLink>
            <MobileNavSep />
            <NavLink to="/howto"        onClick={closeNav}>Guide</NavLink>
            <NavLink to="/capabilities" onClick={closeNav}>Integrations</NavLink>
          </nav>
        )}
      </header>

<<<<<<< HEAD
      {/* Non-blocking connection status (top banner while connecting or on failure).
          The rest of the app (nav, pages, persistent chat) is always usable. */}
      {(showConnectionBanner || isConnecting) && (
        <div style={{
          background: failed ? '#FEF2F2' : '#EFF6FF',
          borderBottom: `1px solid ${failed ? '#FECACA' : '#BFDBFE'}`,
          padding: '6px 16px',
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          color: failed ? '#991B1B' : '#1E40AF'
        }}>
          <span>
            {failed ? '⚠️ Cannot reach backend' : 'Connecting to backend…'}
            {countdown !== null && !failed ? ` (retry in ${countdown}s)` : ''}
            {attempt > 0 ? ` • attempt ${attempt + 1}` : ''}
          </span>
          {failed && (
            <button
              onClick={() => setRetryKey(k => k + 1)}
              style={{ fontSize: 11, padding: '2px 10px', border: '1px solid #FECACA', background: 'white', borderRadius: 4, cursor: 'pointer', color: '#991B1B' }}
            >
              Retry
            </button>
          )}
          <span style={{ marginLeft: 'auto', opacity: 0.7 }}>Chat &amp; pages load independently</span>
        </div>
      )}

      <main className="app-main">{children}</main>

      {chatOpen && (
        <aside className="app-chat" role="complementary" aria-label="AI Concierge chat">
          <ChatContainer />
        </aside>
      )}
=======
      <main className="app-main">{children}</main>

      <aside className="app-chat" role="complementary" aria-label="AI Concierge chat">
        <ChatContainer />
      </aside>
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

      {/* global error banner — position:fixed, bottom of viewport */}
      <ErrorBanner />
    </div>
  );
};

export default Layout;