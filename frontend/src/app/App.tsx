import React, { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import Routes from './routes';
import { useAppStore } from '../state/appStore';

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
    }
  }, []);

  return (
    <React.StrictMode>
      <BrowserRouter>
        <Routes />
        <Analytics />
      </BrowserRouter>
    </React.StrictMode>
  );
};

export default App;
