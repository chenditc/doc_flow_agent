import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import isEqual from 'fast-deep-equal';
import type { TraceSession, TaskExecution } from '../../types/trace';
import { TimelineItem } from './TimelineItem';
import { PendingTaskItem } from './PendingTaskItem';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useDebounce, usePerformanceMonitor } from '../../utils/performanceHooks';

interface TimelineProps {
  trace: TraceSession | null;
  onTaskClick: (task: TaskExecution) => void;
  isLoading?: boolean;
}

const TimelineComponent: React.FC<TimelineProps> = ({
  trace,
  onTaskClick,
  isLoading = false
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [newTaskIndices, setNewTaskIndices] = useState<Set<number>>(new Set());
  const previousTaskCount = useRef<number>(0);

  // Performance monitoring
  usePerformanceMonitor('Timeline render', 50);

  // Debounce task updates to prevent excessive re-renders
  const debouncedTaskExecutions = useDebounce(trace?.task_executions, 100);

  // Get pending tasks: prefer last execution's engine_state_before.task_stack; fallback to end snapshot
  const getPendingTasks = (): string[] => {
    if (!trace) return [];

    const execs = debouncedTaskExecutions || trace.task_executions || [];
    if (execs.length > 0) {
      const lastExec = execs[execs.length - 1];
      const beforeStack = (lastExec as any)?.engine_state_before?.task_stack;
      if (Array.isArray(beforeStack)) {
        return [...beforeStack].reverse();
      }
    }

    const endStack = trace.engine_snapshots?.end?.task_stack;
    if (Array.isArray(endStack)) {
      return [...endStack].reverse();
    }

    return [];
  };

  const pendingTasks = getPendingTasks();

  // Handle pending task clicks
  const handlePendingTaskClick = useCallback((taskDescription: string, index: number) => {
    // For now, pending tasks don't have full task execution objects
    // We could create a synthetic one or handle differently
    console.log(`Clicked pending task: ${taskDescription} at index ${index}`);
  }, []);

  // Memoize the task click handler
  const handleTaskClick = useCallback((task: TaskExecution) => {
    onTaskClick(task);
  }, [onTaskClick]);

  // Handle new task detection and auto-scroll
  useEffect(() => {
    if (!debouncedTaskExecutions) return;

    const currentTaskCount = debouncedTaskExecutions.length;
    const previousCount = previousTaskCount.current;

    if (currentTaskCount > previousCount) {
      // Mark new tasks
      const newIndices = new Set<number>();
      for (let i = previousCount; i < currentTaskCount; i++) {
        newIndices.add(i);
      }
      setNewTaskIndices(newIndices);

      // Auto-scroll to latest task
      scrollToLatest();

      // Remove new task indicators after animation
      setTimeout(() => {
        setNewTaskIndices(new Set());
      }, 3000);
    }

    previousTaskCount.current = currentTaskCount;
  }, [debouncedTaskExecutions]);

  const scrollToLatest = useCallback(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      const lastItem = container.lastElementChild;
      if (lastItem && typeof lastItem.scrollIntoView === 'function') {
        lastItem.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'end'
        });
      }
    }
  }, []);

  // Remove the old handleTaskClick function since we have it defined above

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="large" message="Loading trace data..." />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <h3 className="mt-4 text-sm font-medium text-gray-900">No trace selected</h3>
          <p className="mt-2 text-sm text-gray-500">
            Please select a trace from the dropdown above to view its execution timeline.
          </p>
        </div>
      </div>
    );
  }

  if (!trace.task_executions || trace.task_executions.length === 0) {
    // Check if there are pending tasks even when no executions yet
    const pendingTasksForEmptyState = getPendingTasks();
    
    if (pendingTasksForEmptyState.length > 0) {
      // Show pending tasks even when no executions have started yet
      return (
        <div className="bg-white border border-gray-200 rounded-lg">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Execution Timeline</h2>
                <p className="text-sm text-gray-600 mt-1">
                  No tasks executed yet
                  <span className="text-orange-600 ml-2">
                    • {pendingTasksForEmptyState.length} pending task{pendingTasksForEmptyState.length !== 1 ? 's' : ''}
                  </span>
                </p>
              </div>
              
              {/* Timeline info */}
              <div className="text-right text-sm text-gray-600">
                <div>Started: {new Date(trace.start_time).toLocaleString()}</div>
                {trace.end_time && (
                  <div>Completed: {new Date(trace.end_time).toLocaleString()}</div>
                )}
              </div>
            </div>
          </div>

          {/* Timeline content with only pending tasks */}
          <div 
            ref={containerRef}
            className="max-h-[600px] overflow-y-auto p-6 space-y-4"
            role="log"
            aria-label="Task execution timeline"
          >
            {pendingTasksForEmptyState.map((taskDescription, index) => {
              // With new rule, no pending task is "currently executing"
              const isCurrentlyExecuting = false;
              return (
                <PendingTaskItem
                  key={`empty-pending-${index}`}
                  taskDescription={taskDescription}
                  index={index}
                  totalTasks={pendingTasksForEmptyState.length}
                  isCurrentlyExecuting={isCurrentlyExecuting}
                  onTaskClick={handlePendingTaskClick}
                />
              );
            })}
          </div>

          {/* Scroll to bottom button */}
          {pendingTasksForEmptyState.length > 3 && (
            <div className="flex justify-center pb-4">
              <button
                onClick={scrollToLatest}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                aria-label="Scroll to latest task"
              >
                <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
                Scroll to Latest
              </button>
            </div>
          )}
        </div>
      );
    }
    
    return (
      <div className="text-center py-12">
        <div className="text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-4 text-sm font-medium text-gray-900">No task executions</h3>
          <p className="mt-2 text-sm text-gray-500">
            This trace doesn't contain any task executions yet.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium text-gray-900">Execution Timeline</h2>
            <p className="text-sm text-gray-600 mt-1">
              {trace.task_executions.length} task{trace.task_executions.length !== 1 ? 's' : ''} executed
              {pendingTasks.length > 0 && (
                <span className="text-orange-600 ml-2">
                  • {pendingTasks.length} pending task{pendingTasks.length !== 1 ? 's' : ''}
                </span>
              )}
            </p>
          </div>
          
          {/* Timeline info */}
          <div className="text-right text-sm text-gray-600">
            <div>Started: {new Date(trace.start_time).toLocaleString()}</div>
            {trace.end_time && (
              <div>Completed: {new Date(trace.end_time).toLocaleString()}</div>
            )}
          </div>
        </div>
      </div>

      {/* Timeline content */}
      <div 
        ref={containerRef}
        className="max-h-[600px] overflow-y-auto p-6 space-y-4"
        role="log"
        aria-label="Task execution timeline"
      >
    {(debouncedTaskExecutions || []).map((task, index) => (
          <TimelineItem
            key={task.task_execution_id}
            task={task}
            index={index}
            totalTasks={(debouncedTaskExecutions || []).length + pendingTasks.length}
            onClick={handleTaskClick}
            isNew={newTaskIndices.has(index)}
      isCurrentlyExecuting={index === (debouncedTaskExecutions || []).length - 1}
          />
        ))}
        
        {/* Render pending tasks */}
        {pendingTasks.map((taskDescription, index) => {
          const absoluteIndex = (debouncedTaskExecutions || []).length + index;
          // With new rule, pending tasks are not currently executing
          const isCurrentlyExecuting = false;
          
          return (
            <PendingTaskItem
              key={`pending-${index}`}
              taskDescription={taskDescription}
              index={absoluteIndex}
              totalTasks={(debouncedTaskExecutions || []).length + pendingTasks.length}
              isCurrentlyExecuting={isCurrentlyExecuting}
              onTaskClick={handlePendingTaskClick}
            />
          );
        })}
      </div>

      {/* Scroll to bottom button */}
      {((debouncedTaskExecutions || []).length + pendingTasks.length) > 3 && (
        <div className="flex justify-center pb-4">
          <button
            onClick={scrollToLatest}
            className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            aria-label="Scroll to latest task"
          >
            <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            Scroll to Latest
          </button>
        </div>
      )}
    </div>
  );
};

// Export memoized version for performance
export const Timeline = memo(TimelineComponent, (prevProps, nextProps) => {
  // Re-render when loading toggles or trace data differs deeply
  if (prevProps.isLoading !== nextProps.isLoading) return false;
  return isEqual(prevProps.trace, nextProps.trace);
});
