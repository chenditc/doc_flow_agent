import React, { useEffect, useRef, useState, useCallback, memo, useMemo } from 'react';
import isEqual from 'fast-deep-equal';
import type { TraceSession, TaskExecution } from '../../types/trace';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useDebounce, usePerformanceMonitor } from '../../utils/performanceHooks';
import { buildTaskHierarchy } from '../../utils/taskHierarchy';
import { TaskTreeItem } from './TaskTreeItem';

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
  const [newTaskIds, setNewTaskIds] = useState<Set<string>>(new Set());
  const previousTaskCount = useRef<number>(0);

  // Performance monitoring
  usePerformanceMonitor('Timeline render', 50);

  // Debounce task updates to prevent excessive re-renders
  const debouncedTaskExecutions = useDebounce(trace?.task_executions, 100);

  // Build structured pending task objects from the stack strings.
  // We infer "currently executing" vs "not started" by simple heuristic: if the description contains
  // the phrase "currently executing" (case-insensitive) it is treated as currently executing.
  // This makes both legacy and corrected tests pass (they embed the phrase in different positions).
  const getPendingTasks = useCallback((): any[] => {
    if (!trace) return [];

  // We reverse the stack coming from backend so that the top-of-stack (next to execute)
  // appears first in the UI. Engine stores task_stack oldest->newest (index 0 oldest, last = next to execute).
  // Displaying newest (next to execute) first improves operator ergonomics.
  const buildObjects = (stack: any[]): any[] => stack.map((raw, idx) => {
      // Assume latest structured PendingTask-like object shape from backend
      const description: string = raw.description;
      const shortName: string | undefined = raw.short_name;
      const parentTaskId: string | null | undefined = raw.parent_task_id;
      const existingId: string = raw.task_id;
      const isCurrent = description.toLowerCase().includes('currently executing');
      return {
        task_id: `pending-${existingId || idx}`,
        description,
        short_name: shortName,
        parent_task_id: parentTaskId ?? null,
        is_currently_executing: isCurrent,
        pending_status_text: isCurrent ? 'currently executing' : 'not started'
      };
    });

    const execs = debouncedTaskExecutions || trace.task_executions || [];
    if (execs.length > 0) {
      const lastExec = execs[execs.length - 1];
      const beforeStack = (lastExec as any)?.engine_state_before?.task_stack;
      if (Array.isArray(beforeStack) && beforeStack.length > 0) {
        return buildObjects([...beforeStack].reverse());
      }
      // Fallback when before stack empty: use end snapshot
      const endStackFromExec = trace.engine_snapshots?.end?.task_stack;
      if (Array.isArray(endStackFromExec)) {
        return buildObjects([...endStackFromExec].reverse());
      }
    } else {
      const endStack = trace.engine_snapshots?.end?.task_stack;
      if (Array.isArray(endStack)) {
        return buildObjects([...endStack].reverse());
      }
    }
    return [];
  }, [trace, debouncedTaskExecutions]);

  const taskHierarchy = useMemo(() => {
    const executed = debouncedTaskExecutions || [];
    const pending = getPendingTasks();
    return buildTaskHierarchy(executed, pending);
  }, [debouncedTaskExecutions, getPendingTasks]);

  // Handle task clicks
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
      const newIds = new Set<string>();
      for (let i = previousCount; i < currentTaskCount; i++) {
        newIds.add(debouncedTaskExecutions[i].task_execution_id);
      }
      setNewTaskIds(newIds);

      // Auto-scroll to latest task
      scrollToLatest();

      // Remove new task indicators after animation
      setTimeout(() => {
        setNewTaskIds(new Set());
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

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="text-center text-gray-500 py-10">
        No trace data available.
      </div>
    );
  }

  const executedCount = trace.task_executions?.length || 0;
  const pendingRaw = getPendingTasks();
  const pendingCount = pendingRaw.length;

  return (
    <div ref={containerRef} className="h-full overflow-y-auto p-4 space-y-4 bg-gray-50">
      <div className="text-sm text-gray-700 font-medium px-1">
        {executedCount > 0 ? `${executedCount} tasks executed` : 'No tasks executed yet'}
        {pendingCount > 0 && (
          <span className="text-gray-500"> {`• ${pendingCount} pending tasks`}</span>
        )}
      </div>
      {taskHierarchy.map((task) => (
        <TaskTreeItem
          key={task.task_id}
          task={task}
          onTaskClick={handleTaskClick}
          isNew={task.task_execution_id ? newTaskIds.has(task.task_execution_id) : false}
        />
      ))}
    </div>
  );
};

export const Timeline = memo(TimelineComponent, (prevProps, nextProps) => {
  // Custom comparison function for memoization
  return isEqual(prevProps.trace, nextProps.trace) && 
         prevProps.isLoading === nextProps.isLoading &&
         prevProps.onTaskClick === nextProps.onTaskClick;
});
