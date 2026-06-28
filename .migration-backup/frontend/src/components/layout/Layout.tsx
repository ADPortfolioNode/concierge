import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';

// ── nav group separator ───────────────────────────────────────────────────
const NavSep: React.FC = () => (
  <span className="nav-sep" aria-hidden="true" />
);

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isReady, setIsReady] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Simulate progress up to 90% while waiting for the backend
    const timer = setInterval(() => {
      setProgress(p => (p < 90 ? p + (90 - p) * 0.1 : p));
    }, 500);

    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'ok') {
            setProgress(100);
            setTimeout(() => setIsReady(true), 500); // 500ms delay to smoothly show 100%
            return true;
          }
        }
      } catch (e) {
        // Backend not ready yet, ignore and let it retry
      }
      return false;
    };

    const pollInterval = setInterval(async () => {
      const ready = await checkHealth();
      if (ready) clearInterval(pollInterval);
    }, 2000);

    // Initial check on mount
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
          <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" style={{ height: 48 }} fetchpriority="high" />
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em' }}>Concierge</h1>
        </div>
        <div style={{ width: 300, background: 'rgba(255,255,255,0.1)', borderRadius: 8, overflow: 'hidden', height: 8 }}>
          <div style={{ width: `${progress}%`, background: '#c4b8ff', height: '100%', transition: 'width 0.3s ease-out' }} />
        </div>
        <p style={{ marginTop: 16, color: '#94a3b8', fontSize: 14 }}>
          {progress < 100 ? 'Starting services...' : 'Ready!'}
        </p>
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
            <img src={`${import.meta.env.BASE_URL}logo-optimized.svg`} alt="Concierge" className="brand-logo" style={{ height: 26 }} fetchpriority="high" />
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

      <aside className="concierge-panel" role="complementary" aria-label="AI Concierge chat">
        <ChatContainer />
      </aside>

      {/* global error banner — position:fixed, bottom of viewport */}
      <ErrorBanner />

      <main className="context-panel">{children}</main>
    </div>
  );
};

export default Layout;