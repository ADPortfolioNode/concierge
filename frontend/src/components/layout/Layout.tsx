import React from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import ErrorBanner from '../ui/ErrorBanner';
import MediaStage from '../media/MediaStage';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // responsive layout styles handled via CSS grid in index.css
  return (
    <div className="app-container" style={{ height: '100vh' }}>
      <header className="app-header">
        <div className="header-inner">
          <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <NavLink to="/" end style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
              <img src="/logo-optimized.svg" alt="Concierge" className="brand-logo" style={{ height: 28 }} />
              <span style={{ color: '#c4b8ff', fontWeight: 800, fontSize: 16, letterSpacing: '-0.01em' }}>Concierge</span>
            </NavLink>
          </div>
          <nav className="header-nav">
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/goals">Goals</NavLink>
            <NavLink to="/tasks">Tasks</NavLink>
            <NavLink to="/workspace">Workspace</NavLink>
            <NavLink to="/strategy">Strategy</NavLink>
            <NavLink to="/howto">How&#8209;To</NavLink>
            <NavLink to="/capabilities">Capabilities</NavLink>
          </nav>
        </div>
      </header>

      <aside className="concierge-panel" role="complementary">
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