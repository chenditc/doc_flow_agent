import React from 'react';
import type { TaskExecution } from '../../types/trace';

interface TaskSummaryProps {
  task: TaskExecution;
}

export const TaskSummary: React.FC<TaskSummaryProps> = ({ task }) => {
  const formatTime = (timestamp: string | null): string => {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleString();
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

  return (
    <div className="space-y-4">
      {/* Task Description */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Task Description</h3>
        <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-md break-words whitespace-pre-wrap overflow-wrap-anywhere">
          {task.task_description || 'No description available'}
        </p>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Execution ID:</span>
            <span className="font-mono text-gray-600 break-all text-right ml-2">
              {task.task_execution_id}
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Execution Counter:</span>
            <span className="text-gray-600">{task.task_execution_counter}</span>
          </div>

          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Status:</span>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(task.status)}`}>
              {task.status}
            </span>
          </div>
        </div>

        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Started:</span>
            <span className="text-gray-600">{formatTime(task.start_time)}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Ended:</span>
            <span className="text-gray-600">{formatTime(task.end_time)}</span>
          </div>

          <div className="flex justify-between">
            <span className="font-medium text-gray-700">Duration:</span>
            <span className="text-gray-600">{calculateDuration(task.start_time, task.end_time)}</span>
          </div>
        </div>
      </div>

      {/* Error */}
      {task.error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <h4 className="text-sm font-medium text-red-800 mb-1">Error</h4>
          <p className="text-sm text-red-700 font-mono whitespace-pre-wrap">
            {task.error}
          </p>
        </div>
      )}
    </div>
  );
};
