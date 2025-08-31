import React from 'react';
import type { TaskExecution } from '../../types/trace';

interface TimelineItemProps {
  task: TaskExecution;
  index: number;
  totalTasks: number;
  onClick: (task: TaskExecution) => void;
  isNew?: boolean;
  isCurrentlyExecuting?: boolean;
}

export const TimelineItem: React.FC<TimelineItemProps> = ({
  task,
  index,
  totalTasks,
  onClick,
  isNew = false,
  isCurrentlyExecuting = false
}) => {
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'border-green-400 bg-green-50';
      case 'error':
        return 'border-red-400 bg-red-50';
      case 'running':
        return 'border-blue-400 bg-blue-50';
      case 'cancelled':
        return 'border-yellow-400 bg-yellow-50';
      default:
        return 'border-gray-400 bg-gray-50';
    }
  };

  const getStatusBadgeColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'cancelled':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTime = (timestamp: string): string => {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch (error) {
      return 'Invalid time';
    }
  };

  const calculateDuration = (startTime: string, endTime: string | null): string => {
    if (!startTime || !endTime) return 'N/A';
    
    try {
      const start = new Date(startTime);
      const end = new Date(endTime);
      const diffMs = end.getTime() - start.getTime();
      const diffSec = Math.round(diffMs / 1000);
      
      if (diffSec < 60) {
        return `${diffSec}s`;
      } else {
        const minutes = Math.floor(diffSec / 60);
        const seconds = diffSec % 60;
        return `${minutes}m ${seconds}s`;
      }
    } catch (error) {
      return 'Invalid duration';
    }
  };

  const extractTaskOutput = (task: TaskExecution): string => {
    // Try to get from engine_state_after.context.last_task_output
    if (task.engine_state_after && 
        task.engine_state_after.context && 
        task.engine_state_after.context.last_task_output) {
      
      const output = task.engine_state_after.context.last_task_output;
      
      if (typeof output === 'string') {
        return output;
      } else if (typeof output === 'object' && output !== null) {
        if (output.stdout || output.stderr) {
          let result = '';
          if (output.stdout) result += output.stdout;
          if (output.stderr) result += (result ? '\n--- STDERR ---\n' : '') + output.stderr;
          return result || 'No output';
        } else {
          return JSON.stringify(output, null, 2);
        }
      }
    }
    
    return 'No output available';
  };

  const extractPhases = (task: TaskExecution): string[] => {
    if (!task.phases) return [];
    return Object.keys(task.phases);
  };

  const handleClick = () => {
    onClick(task);
  };

  const duration = calculateDuration(task.start_time, task.end_time);
  const phases = extractPhases(task);
  const output = extractTaskOutput(task);
  const hasConnector = index < totalTasks - 1;

  const containerStatusClass = isCurrentlyExecuting
    ? 'border-orange-400 bg-orange-50'
    : getStatusColor(task.status);

  const shouldShowStatusBadge = !(isCurrentlyExecuting && task.status === 'completed');

  return (
    <div 
      className={`timeline-item relative cursor-pointer group ${isNew ? 'animate-pulse' : ''}`}
      onClick={handleClick}
    >
      {/* Connector line */}
      {hasConnector && (
        <div className="absolute left-6 top-full w-0.5 h-8 bg-gray-300 z-0 pointer-events-none" />
      )}

  <div className={`relative z-10 bg-gray-50 rounded-lg p-4 border-l-4 transition-all duration-200 group-hover:shadow-md ${containerStatusClass} ${isCurrentlyExecuting ? 'ring-2 ring-orange-300' : ''}`}>
        {/* Task Header */}
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1 min-w-0 pr-4">
            <h3 className="text-sm font-semibold text-gray-900 truncate" title={task.task_description}>
              {task.task_description || `Task ${task.task_execution_counter}`}
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              ID: <span className="font-mono">{task.task_execution_id}</span>
            </p>
          </div>
          <div className="flex-shrink-0 text-right">
            <div className="flex items-center gap-1 flex-wrap justify-end">
              {shouldShowStatusBadge && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(task.status)}`}>
                  {task.status}
                </span>
              )}
              {isCurrentlyExecuting && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                  currently executing
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Task Details */}
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-600 mb-3">
          <div>
            <span className="font-medium">Started:</span> {formatTime(task.start_time)}
          </div>
          <div>
            <span className="font-medium">Duration:</span> {duration}
          </div>
        </div>

        {/* Phases */}
        {phases.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-medium text-gray-700 mb-1">Phases:</div>
            <div className="flex flex-wrap gap-1">
              {phases.map((phase) => (
                <span 
                  key={phase}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700"
                >
                  {phase.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Output Preview */}
        {output && output !== 'No output available' && (
          <div className="border-t border-gray-200 pt-2">
            <div className="text-xs font-medium text-gray-700 mb-1">Output Preview:</div>
            <div className="text-xs text-gray-600 bg-white rounded px-2 py-1 max-h-16 overflow-hidden">
              <pre className="whitespace-pre-wrap break-words">
                {output.length > 100 ? output.substring(0, 100) + '...' : output}
              </pre>
            </div>
          </div>
        )}

        {/* Error display */}
        {task.error && (
          <div className="border-t border-red-200 pt-2 mt-2">
            <div className="text-xs font-medium text-red-700 mb-1">Error:</div>
            <div className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">
              {task.error}
            </div>
          </div>
        )}

        {/* Click indicator */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </div>
      </div>
    </div>
  );
};
