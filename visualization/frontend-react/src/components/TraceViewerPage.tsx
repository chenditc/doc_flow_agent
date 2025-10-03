/**
 * Trace viewer page component
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTraceContext } from '../context/TraceContext';
import { TraceSelector } from './TraceSelector/TraceSelector';
import { Timeline } from './Timeline/Timeline';
import { TaskDetailsModal } from './TaskDetails/TaskDetailsModal';
import { LoadingSpinner, LoadingState, SkeletonTimeline } from './common/LoadingStates';
import { ConnectionStatus } from './common/ConnectionIndicators';
import { useTrace } from '../hooks/useTraceData';
import { useRealtime } from '../hooks/useRealtime';
import { useAnnouncement } from '../utils/accessibility';
import type { TaskExecution } from '../types/trace';

export const TraceViewerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(
    searchParams.get('trace') || null
  );
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

  // Sync local selected trace id (initialized from URL) into context so hooks relying
  // on context (e.g. realtime subscription / invalidation) have the correct value
  // even before the user manually re-selects a trace.
  useEffect(() => {
    if (selectedTraceId !== state.selectedTraceId) {
      setCtxSelectedTraceId(selectedTraceId);
    }
  }, [selectedTraceId, state.selectedTraceId, setCtxSelectedTraceId]);

  // Update URL when trace selection changes
  useEffect(() => {
    if (selectedTraceId) {
      setSearchParams({ trace: selectedTraceId });
    } else {
      setSearchParams({});
    }
  }, [selectedTraceId, setSearchParams]);

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
    <>
      <AnnouncerComponent />
      
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
    </>
  );
};