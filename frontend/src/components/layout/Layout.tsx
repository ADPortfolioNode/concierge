import React from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';
import MediaStage from '../media/MediaStage';

// ── nav group separator ───────────────────────────────────────────────────
const NavSep: React.FC = () => (
  <span aria-hidden="true" style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.1)', display: 'inline-block', flexShrink: 0 }} />
);

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // responsive layout styles handled via CSS grid in index.css
  return (
    <div className="app-container" style={{ height: '100vh' }}>
      <header className="app-header">
        <div className="header-inner">
          <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <NavLink to="/" end style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
              <img src="/logo-optimized.svg" alt="Concierge" className="brand-logo" style={{ height: 26 }} />
              <span style={{ color: '#c4b8ff', fontWeight: 800, fontSize: 15, letterSpacing: '-0.01em' }}>Concierge</span>
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

      {/* Floating, draggable media stage — renders itself when store has content */}
      <MediaStage />
    </div>
  );
};

export default Layout;