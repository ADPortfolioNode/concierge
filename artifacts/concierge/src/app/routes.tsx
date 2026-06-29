import React, { Suspense, Component, ErrorInfo } from 'react';
import { Routes as Switch, Route, Navigate } from 'react-router-dom';

const HomePage = React.lazy(() => import('../features/concierge/HomePage'));
const TasksPage = React.lazy(() => import('../features/tasks/TasksPage'));
const TaskStatusPage = React.lazy(() => import('../features/tasks/TaskStatusPage'));
const GoalsPage = React.lazy(() => import('../features/goals/GoalsPage'));
const WorkspacePage = React.lazy(() => import('../features/workspace/WorkspacePage'));
const MediaPage = React.lazy(() => import('../features/media/MediaPage'));
const StrategyPage = React.lazy(() => import('../features/strategy/StrategyPage'));
const HowToPage = React.lazy(() => import('../features/concierge/HowToPage'));
const CapabilitiesPage = React.lazy(() => import('../features/capabilities/CapabilitiesPage'));

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
            <Route path="/tasks/:taskId" element={<TaskStatusPage />} />
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