import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TraceContextProvider } from './context/TraceContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Navigation } from './components/Navigation';
import { TraceViewerPage } from './components/TraceViewerPage';
import { JobsListPage, JobDetailPage } from './components/Jobs';
import { useAnnouncement } from './utils/accessibility';

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
  const { announce } = useAnnouncement();

  // DebugPendingPage removed to simplify routing; query param based debug mode eliminated.

  return (
    <ErrorBoundary 
      onError={(error) => {
        console.error('App error:', error);
        announce('An unexpected error occurred', 'assertive');
      }}
    >
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main role="main" aria-label="Application content">
          <Routes>
            <Route path="/" element={<JobsListPage />} />
            <Route path="/jobs" element={<JobsListPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/traces" element={<TraceViewerPage />} />
          </Routes>
        </main>
      </div>
    </ErrorBoundary>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TraceContextProvider baseUrl={window.location.origin}>
        <AppContent />
      </TraceContextProvider>
    </QueryClientProvider>
  );
}

export default App;
