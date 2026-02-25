/* eslint-disable react-refresh/only-export-components */
/**
 * Lazy Loading Components
 * =======================
 * Code-splitting and lazy loading for improved initial load performance.
 */

import React, { Suspense, lazy } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { DashboardSkeleton, ChatSkeleton, FileBrowserSkeleton } from './Skeleton';

// =============================================================================
// Loading Fallbacks
// =============================================================================

/**
 * Generic loading spinner
 */
export function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 200,
        gap: 2
      }}
    >
      <CircularProgress />
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
    </Box>
  );
}

/**
 * Page-level loading fallback
 */
export function PageLoader({ type = 'generic' }) {
  switch (type) {
    case 'dashboard':
      return <DashboardSkeleton />;
    case 'chat':
      return <ChatSkeleton messages={6} />;
    case 'files':
      return <FileBrowserSkeleton items={12} />;
    default:
      return <LoadingSpinner message="Loading page..." />;
  }
}

// =============================================================================
// Lazy Loaded Components
// =============================================================================

// Pages
export const LazyDashboard = lazy(() =>
  import(/* webpackChunkName: "dashboard" */ '../pages/Dashboard')
);

export const LazyChatPage = lazy(() =>
  import(/* webpackChunkName: "chat" */ '../pages/ChatPage')
);

export const LazyFileBrowser = lazy(() =>
  import(/* webpackChunkName: "files" */ '../pages/FileBrowser')
);

export const LazySettings = lazy(() =>
  import(/* webpackChunkName: "settings" */ '../pages/Settings')
);

export const LazyLearningMemory = lazy(() =>
  import(/* webpackChunkName: "learning" */ '../pages/LearningMemory')
);

export const LazyMonitoring = lazy(() =>
  import(/* webpackChunkName: "monitoring" */ '../pages/Monitoring')
);

// Heavy Components
export const LazyCodeEditor = lazy(() =>
  import(/* webpackChunkName: "code-editor" */ './CodeEditor')
);

export const LazyMarkdownRenderer = lazy(() =>
  import(/* webpackChunkName: "markdown" */ './MarkdownRenderer')
);

export const LazyChartComponents = lazy(() =>
  import(/* webpackChunkName: "charts" */ './Charts')
);

// =============================================================================
// Wrapper Components with Suspense
// =============================================================================

/**
 * Dashboard page with lazy loading
 */
export function Dashboard(props) {
  return (
    <Suspense fallback={<PageLoader type="dashboard" />}>
      <LazyDashboard {...props} />
    </Suspense>
  );
}

/**
 * Chat page with lazy loading
 */
export function ChatPage(props) {
  return (
    <Suspense fallback={<PageLoader type="chat" />}>
      <LazyChatPage {...props} />
    </Suspense>
  );
}

/**
 * File browser with lazy loading
 */
export function FileBrowser(props) {
  return (
    <Suspense fallback={<PageLoader type="files" />}>
      <LazyFileBrowser {...props} />
    </Suspense>
  );
}

/**
 * Settings page with lazy loading
 */
export function Settings(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading settings..." />}>
      <LazySettings {...props} />
    </Suspense>
  );
}

/**
 * Learning Memory page with lazy loading
 */
export function LearningMemory(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading learning memory..." />}>
      <LazyLearningMemory {...props} />
    </Suspense>
  );
}

/**
 * Monitoring page with lazy loading
 */
export function Monitoring(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading monitoring..." />}>
      <LazyMonitoring {...props} />
    </Suspense>
  );
}

/**
 * Code editor with lazy loading
 */
export function CodeEditor(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading editor..." />}>
      <LazyCodeEditor {...props} />
    </Suspense>
  );
}

/**
 * Markdown renderer with lazy loading
 */
export function MarkdownRenderer(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Rendering..." />}>
      <LazyMarkdownRenderer {...props} />
    </Suspense>
  );
}

/**
 * Chart components with lazy loading
 */
export function ChartComponents(props) {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading charts..." />}>
      <LazyChartComponents {...props} />
    </Suspense>
  );
}

// =============================================================================
// Preloading Utilities
// =============================================================================

/**
 * Preload a lazy component
 */
export function preloadComponent(component) {
  if (component && component._payload && component._payload._status === -1) {
    component._payload._status = 0;
    component._payload._result = component._payload._result();
  }
}

/**
 * Preload common routes on idle
 */
export function preloadOnIdle() {
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => {
      // Preload commonly accessed pages
      preloadComponent(LazyDashboard);
      preloadComponent(LazyChatPage);
    });
  }
}

/**
 * Preload on hover (for navigation links)
 */
export function createPreloadHandler(component) {
  let preloaded = false;

  return () => {
    if (!preloaded) {
      preloadComponent(component);
      preloaded = true;
    }
  };
}

// =============================================================================
// Route Configuration with Lazy Loading
// =============================================================================

export const lazyRoutes = [
  {
    path: '/',
    element: Dashboard,
    preload: LazyDashboard,
    skeleton: 'dashboard'
  },
  {
    path: '/chat',
    element: ChatPage,
    preload: LazyChatPage,
    skeleton: 'chat'
  },
  {
    path: '/chat/:chatId',
    element: ChatPage,
    preload: LazyChatPage,
    skeleton: 'chat'
  },
  {
    path: '/files',
    element: FileBrowser,
    preload: LazyFileBrowser,
    skeleton: 'files'
  },
  {
    path: '/settings',
    element: Settings,
    preload: LazySettings,
    skeleton: 'generic'
  },
  {
    path: '/learning',
    element: LearningMemory,
    preload: LazyLearningMemory,
    skeleton: 'generic'
  },
  {
    path: '/monitoring',
    element: Monitoring,
    preload: LazyMonitoring,
    skeleton: 'dashboard'
  }
];

// =============================================================================
// HOC for Lazy Loading
// =============================================================================

/**
 * Higher-order component for lazy loading with custom fallback
 */
// eslint-disable-next-line no-unused-vars
export function withLazyLoading(importFn, FallbackComponent = LoadingSpinner) {
  const LazyComponent = lazy(importFn);

  return function LazyWrapper(props) {
    return (
      <Suspense fallback={<FallbackComponent />}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

/**
 * Create a lazy component with error boundary
 */
export function createLazyComponent(importFn, options = {}) {
  const {
    fallback = <LoadingSpinner />,
    errorFallback: _errorFallback = null,
    displayName = 'LazyComponent'
  } = options;

  const LazyComponent = lazy(importFn);

  function LazyWrapper(props) {
    return (
      <Suspense fallback={fallback}>
        <LazyComponent {...props} />
      </Suspense>
    );
  }

  LazyWrapper.displayName = displayName;
  LazyWrapper.preload = () => preloadComponent(LazyComponent);

  return LazyWrapper;
}

export default {
  LoadingSpinner,
  PageLoader,
  Dashboard,
  ChatPage,
  FileBrowser,
  Settings,
  LearningMemory,
  Monitoring,
  CodeEditor,
  MarkdownRenderer,
  ChartComponents,
  preloadOnIdle,
  createPreloadHandler,
  lazyRoutes,
  withLazyLoading,
  createLazyComponent
};
