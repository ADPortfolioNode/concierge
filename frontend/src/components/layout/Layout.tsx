import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import ChatContainer from '../chat/ChatContainer';
import MediaRenderer from '../media/MediaRenderer';
import ErrorBanner from '../ui/ErrorBanner';
import { useViewport } from '@/utils/useViewport';
import { useAppStore } from '@/state/appStore';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const viewport = useViewport();
  const [mediaOpen, setMediaOpen] = useState(false);
  const activeMedia = useAppStore((s) => s.activeMedia);
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);
  const hasMedia = !!activeMedia;

  useEffect(() => {
    if (hasMedia && (viewport.isLaptop || viewport.isDesktop)) {
      setMediaOpen(true);
    } else {
      setMediaOpen(false);
    }
  }, [hasMedia, viewport.isLaptop, viewport.isDesktop]);

  const renderMedia = () => (
    <div className="media-panel" style={{ padding: 'var(--space-4)' }}>
      <button onClick={() => setActiveMedia(null)}>Close</button>
      {/* actual media component would use store meta.media */}
      <MediaRenderer media={{ type: 'image', url: activeMedia, overlay_text: null, mime_type: 'image/jpeg' }} />
    </div>
  );

  // responsive layout styles handled via CSS grid in index.css
  return (
    <div className="app-container" style={{ height: '100vh' }}>
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <NavLink to="/" end style={{ color: '#c4b8ff', fontWeight: 800, fontSize: 16, letterSpacing: '-0.01em', borderBottom: 'none' }}>Concierge</NavLink>
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

      {/* global error banner appears below panels */}
      <ErrorBanner />

      <main className="context-panel">{children}</main>

      {(viewport.isLaptop || viewport.isDesktop) && (
        <div className={`media-overlay ${mediaOpen ? 'open' : ''}`}>{renderMedia()}</div>
      )}

      {viewport.isMobile && hasMedia && (
        <button className="media-toggle" onClick={() => setMediaOpen(!mediaOpen)} aria-pressed={mediaOpen}>
          Toggle Media
        </button>
      )}
    </div>
  );
};

export default Layout;