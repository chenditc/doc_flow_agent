import React from 'react';

interface PendingTaskItemProps {
  taskDescription: string;
  index: number;
  totalTasks: number;
  isCurrentlyExecuting?: boolean;
  onTaskClick?: (taskDescription: string, index: number) => void;
}

export const PendingTaskItem: React.FC<PendingTaskItemProps> = ({
  taskDescription,
  index,
  totalTasks,
  isCurrentlyExecuting = false,
  onTaskClick
}) => {
  const getStatusColor = (): string => {
    if (isCurrentlyExecuting) {
      return 'border-orange-400 bg-orange-50';
    }
    return 'border-gray-300 bg-gray-50';
  };

  const getStatusBadgeColor = (): string => {
    if (isCurrentlyExecuting) {
      return 'bg-orange-100 text-orange-800';
    }
    return 'bg-gray-100 text-gray-600';
  };

  const getStatusText = (): string => {
    if (isCurrentlyExecuting) {
      return 'currently executing';
    }
    return 'not started';
  };

  const handleClick = () => {
    if (onTaskClick) {
      onTaskClick(taskDescription, index);
    }
  };

  const hasConnector = index < totalTasks - 1;

  return (
    <div 
      className={`timeline-item relative ${onTaskClick ? 'cursor-pointer' : ''} group`}
      onClick={handleClick}
    >
      {/* Connector line */}
      {hasConnector && (
        <div className="absolute left-6 top-full w-0.5 h-8 bg-gray-300 z-0 pointer-events-none" />
      )}

  <div className={`relative z-10 bg-gray-50 rounded-lg p-4 border-l-4 transition-all duration-200 ${onTaskClick ? 'group-hover:shadow-md' : ''} ${getStatusColor()}`}>
        {/* Task Header */}
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1 min-w-0 pr-4">
            <h3 className="text-sm font-semibold text-gray-700 truncate" title={taskDescription}>
              {taskDescription.length > 100 ? `${taskDescription.substring(0, 100)}...` : taskDescription}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Pending Task #{index + 1}
            </p>
          </div>
          <div className="flex-shrink-0 text-right">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>

        {/* Task Details */}
        <div className="text-xs text-gray-500 mb-3">
          <div>
            <span className="font-medium">Status:</span> Waiting in task stack
          </div>
          {isCurrentlyExecuting && (
            <div className="text-orange-600 mt-1">
              <span className="font-medium">⚠️ This task is currently being executed</span>
            </div>
          )}
        </div>

        {/* Full description in collapsed area for long tasks */}
        {taskDescription.length > 100 && (
          <details className="mt-2">
            <summary className="text-xs text-blue-600 cursor-pointer hover:text-blue-800">
              Show full description
            </summary>
            <div className="mt-2 p-2 bg-white rounded text-xs text-gray-700 border">
              {taskDescription}
            </div>
          </details>
        )}

        {/* Click indicator */}
        {onTaskClick && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
};
