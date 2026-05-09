import React, { useEffect, Component, ErrorInfo } from 'react';
import { BrowserRouter } from 'react-router-dom';
import Routes from './routes';
import { useAppStore } from '../state/appStore';

class AppErrorBoundary extends Component<{}, { hasError: boolean; error?: Error }> {
  constructor(props: {}) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App error boundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="app-error-boundary">
          <h1 className="app-error-boundary__title">Something went wrong</h1>
          <p>The application encountered an error while loading. Please refresh or check the console for details.</p>
          <pre className="app-error-boundary__stack">{this.state.error?.message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const App: React.FC = () => {
  useEffect(() => {
    console.log('App effect running - exposing store');
    if (typeof window !== 'undefined') {
      (window as any).__APP_HOOK__ = useAppStore;
      (window as any).__APP_STORE__ = useAppStore.getState();
      useAppStore.subscribe((s) => {
        (window as any).__APP_STORE__ = s;
      });
    }
  }, []);

  return (
    <React.StrictMode>
      <AppErrorBoundary>
        <BrowserRouter basename={import.meta.env.BASE_URL}>
          <Routes />
        </BrowserRouter>
      </AppErrorBoundary>
    </React.StrictMode>
  );
};

export default App;