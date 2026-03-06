import React, { Suspense, lazy } from 'react';
import { Routes as Switch, Route, Navigate } from 'react-router-dom';

// lazy-loaded pages
const HomePage = lazy(() => import('../features/concierge/HomePage'));
const TasksPage = lazy(() => import('../features/tasks/TasksPage'));
const GoalsPage = lazy(() => import('../features/goals/GoalsPage'));
const WorkspacePage = lazy(() => import('../features/workspace/WorkspacePage'));
const StrategyPage = lazy(() => import('../features/strategy/StrategyPage'));
const HowToPage = lazy(() => import('../features/concierge/HowToPage'));
const CapabilitiesPage = lazy(() => import('../features/capabilities/CapabilitiesPage'));

import Layout from '../components/layout/Layout';

const Routes: React.FC = () => {
  return (
    <Layout>
      <Suspense fallback={<div>Loading...</div>}>
        <Switch>
          <Route path="/" element={<HomePage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/strategy" element={<StrategyPage />} />
          <Route path="/howto" element={<HowToPage />} />
          <Route path="/capabilities" element={<CapabilitiesPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Switch>
      </Suspense>
    </Layout>
  );
};

export default Routes;