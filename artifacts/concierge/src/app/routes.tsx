import React, { Suspense, Component, ErrorInfo } from 'react';
import { Routes as Switch, Route, Navigate } from 'react-router-dom';

// eager-loaded pages (avoids Suspense/lazy issues with dual React instances)
import HomePage from '../features/concierge/HomePage';
import TasksPage from '../features/tasks/TasksPage';
import GoalsPage from '../features/goals/GoalsPage';
import WorkspacePage from '../features/workspace/WorkspacePage';
import MediaPage from '../features/media/MediaPage';
import StrategyPage from '../features/strategy/StrategyPage';
import HowToPage from '../features/concierge/HowToPage';
import CapabilitiesPage from '../features/capabilities/CapabilitiesPage';

import Layout from '../components/layout/Layout';

class RouteErrorBoundary extends Component<{ children: React.ReactNode }, { error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[RouteErrorBoundary] page load error:', error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, color: '#fca5a5', fontFamily: 'monospace' }}>
          <strong>Page failed to load:</strong>
          <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{this.state.error.message}</pre>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, opacity: 0.7 }}>{this.state.error.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const Routes: React.FC = () => {
  return (
    <Layout>
      <RouteErrorBoundary>
        <Suspense fallback={<div style={{ padding: 32, color: '#94a3b8' }}>Loading page...</div>}>
          <Switch>
            <Route path="/" element={<HomePage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/workspace" element={<WorkspacePage />} />
            <Route path="/media" element={<MediaPage />} />
            <Route path="/strategy" element={<StrategyPage />} />
            <Route path="/howto" element={<HowToPage />} />
            <Route path="/capabilities" element={<CapabilitiesPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Switch>
        </Suspense>
      </RouteErrorBoundary>
    </Layout>
  );
};

export default Routes;