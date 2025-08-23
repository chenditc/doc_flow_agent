import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TraceContextProvider, useTraceContext } from './context/TraceContext';
import { Header } from './components/common/Header';
import { TraceSelector } from './components/TraceSelector/TraceSelector';
import { Timeline } from './components/Timeline/Timeline';
import { TaskDetailsModal } from './components/TaskDetails/TaskDetailsModal';
import { LoadingSpinner, LoadingState, SkeletonTimeline } from './components/common/LoadingStates';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ConnectionStatus } from './components/common/ConnectionIndicators';
import { useTrace } from './hooks/useTraceData';
import { useRealtime } from './hooks/useRealtime';
import { useAnnouncement } from './utils/accessibility';
import type { TaskExecution } from './types/trace';

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
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskExecution | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);

  const { state, setSelectedTraceId: setCtxSelectedTraceId } = useTraceContext();
  const { announce, AnnouncerComponent } = useAnnouncement();

  const {
    data: trace,
    isLoading: traceLoading,
    error: traceError,
  } = useTrace(selectedTraceId);

  // Initialize real-time monitoring
  useRealtime({
    onMessage: (message) => {
      console.log('Real-time message received:', message);
      announce('Trace data updated', 'polite');
    },
    onError: (error) => {
      console.error('Real-time error:', error);
      announce(`Connection error: ${error.message}`, 'assertive');
    }
  });

  const handleTraceSelected = (traceId: string | null) => {
    setSelectedTraceId(traceId);
  // Keep context in sync for components/hooks depending on context-selected trace
  setCtxSelectedTraceId(traceId);
    // Close task modal when switching traces
    setIsTaskModalOpen(false);
    setSelectedTask(null);
    
    if (traceId) {
      announce(`Selected trace ${traceId}`, 'polite');
    }
  };

  const handleTaskClick = (task: TaskExecution) => {
    setSelectedTask(task);
    setIsTaskModalOpen(true);
    announce(`Opened task details for ${task.task_description}`, 'polite');
  };

  const handleCloseTaskModal = () => {
    setIsTaskModalOpen(false);
    setSelectedTask(null);
    announce('Closed task details', 'polite');
  };

  return (
    <ErrorBoundary 
      onError={(error) => {
        console.error('App error:', error);
        announce('An unexpected error occurred', 'assertive');
      }}
    >
      <div className="min-h-screen bg-gray-50">
        <AnnouncerComponent />
        <Header />
        
        <div className="fixed top-4 right-4 z-50">
          <ConnectionStatus
            isConnected={state.isConnected}
            error={state.connectionError || undefined}
            isEnabled={state.isRealTimeEnabled}
          />
        </div>
        
        <main 
          className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
          role="main"
          aria-label="Trace visualization dashboard"
        >
          <div className="space-y-6">
            {/* Trace Selector */}
            <section aria-label="Trace selection">
              <TraceSelector
                selectedTraceId={selectedTraceId}
                onTraceSelected={handleTraceSelected}
                isLoading={traceLoading}
              />
            </section>

            {/* Main Content */}
            <section aria-label="Trace timeline">
              <LoadingState
                isLoading={traceLoading}
                error={traceError instanceof Error ? traceError.message : traceError}
                loadingComponent={
                  <div className="space-y-4">
                    <div className="text-center py-4">
                      <LoadingSpinner size="lg" className="text-blue-600 mb-2" />
                      <p className="text-sm text-gray-600">Loading trace data...</p>
                    </div>
                    <SkeletonTimeline />
                  </div>
                }
                minHeight="min-h-64"
              >
                <Timeline
                  trace={trace || null}
                  onTaskClick={handleTaskClick}
                  isLoading={traceLoading}
                />
              </LoadingState>
            </section>
          </div>

          {/* Task Details Modal */}
          <TaskDetailsModal
            isOpen={isTaskModalOpen}
            onClose={handleCloseTaskModal}
            task={selectedTask}
          />
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
