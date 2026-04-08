import React, { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import Routes from './routes';
import { useAppStore } from '../state/appStore';
import { makeAssetUrl } from '../config/activeServer';

const App: React.FC = () => {
  // expose store helpers to window after client mounts; avoids build-time
  // dead-code elimination issues with direct module-level assignments.
  useEffect(() => {
    console.log('App effect running - exposing store');
    if (typeof window !== 'undefined') {
      // hook gives access to actions
      (window as any).__APP_HOOK__ = useAppStore;
      // snapshot will be kept up-to-date below
      (window as any).__APP_STORE__ = useAppStore.getState();
      useAppStore.subscribe((s) => {
        (window as any).__APP_STORE__ = s;
      });

      // Optional environment-provided custom stylesheet (dynamic staging/prod path)
      const sheetUrl = import.meta.env.VITE_STYLESHEET_URL ? import.meta.env.VITE_STYLESHEET_URL : makeAssetUrl('/styles/concierge.css');
      if (sheetUrl) {
        const existing = document.getElementById('dynamic-custom-css') as HTMLLinkElement | null;
        if (!existing || existing.href !== sheetUrl) {
          if (existing) existing.remove();
          const link = document.createElement('link');
          link.id = 'dynamic-custom-css';
          link.rel = 'stylesheet';
          link.href = sheetUrl;
          document.head.appendChild(link);
        }
      }
    }
  }, []);

  return (
    <React.StrictMode>
      <BrowserRouter>
        <Routes />
      </BrowserRouter>
    </React.StrictMode>
  );
};

export default App;