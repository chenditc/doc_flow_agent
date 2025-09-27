import { useMemo } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TraceContextProvider } from './context/TraceContext';
import { Header } from './components/common/Header';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Navigation } from './components/Navigation';
import { TraceViewerPage } from './components/TraceViewerPage';
import { JobsListPage, JobDetailPage } from './components/Jobs';
import { useAnnouncement } from './utils/accessibility';
import { DebugPendingPage } from './debug/DebugPendingPage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppContent() {
  const location = useLocation();
  const { announce } = useAnnouncement();

  // Lightweight debug route switch (driven by query string)
  const debugMode = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('debug');
  }, [location.search]);

  if (debugMode === 'pending') {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <DebugPendingPage />
        </main>
      </div>
    );
  }

  return (
    <ErrorBoundary 
      onError={(error) => {
        console.error('App error:', error);
        announce('An unexpected error occurred', 'assertive');
      }}
    >
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        <Routes>
          <Route path="/" element={<TraceViewerPage />} />
          <Route path="/jobs" element={<JobsListPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </div>
    </ErrorBoundary>
  );
}function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TraceContextProvider baseUrl={window.location.origin}>
        <AppContent />
      </TraceContextProvider>
    </QueryClientProvider>
  );
}

export default App;
