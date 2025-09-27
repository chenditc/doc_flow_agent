import React, { useState } from 'react';

interface PendingTaskItemProps {
  taskDescription: string;
  shortName?: string;
  onClick?: (taskDescription: string) => void;
  // Injected optional flags from heuristic in Timeline
  pendingStatusText?: string; // 'currently executing' | 'not started' | 'pending'
  isCurrent?: boolean;
}

export const PendingTaskItem: React.FC<PendingTaskItemProps> = ({
  taskDescription,
  shortName,
  onClick,
  pendingStatusText,
  isCurrent
}) => {
  const [showFullDescription, setShowFullDescription] = useState(false);
  const isCurrentlyExecuting = !!isCurrent || (pendingStatusText?.toLowerCase() === 'currently executing');

  const getStatusColor = (): string => {
    if (isCurrentlyExecuting) return 'border-orange-400 bg-orange-50';
    return 'border-gray-300 bg-gray-50';
  };

  const getStatusBadgeColor = (): string => {
    if (isCurrentlyExecuting) return 'bg-orange-100 text-orange-800';
    return 'bg-gray-100 text-gray-600';
  };

  const getStatusText = (): string => {
    if (pendingStatusText) return pendingStatusText;
    return isCurrentlyExecuting ? 'currently executing' : 'pending';
  };

  const handleClick = () => {
    if (onClick) {
      onClick(taskDescription);
    }
  };

  return (
    <div 
      className={`timeline-item relative ${onClick ? 'cursor-pointer' : ''} group`}
      onClick={handleClick}
    >
      <div className={`relative z-10 bg-gray-50 rounded-lg p-3 border-l-4 transition-all duration-200 ${onClick ? 'group-hover:shadow-md' : ''} ${getStatusColor()}`}>
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0 pr-4">
            <h3 className="text-sm font-semibold text-gray-700 truncate" title={shortName || taskDescription}>
              {shortName || taskDescription}
            </h3>
          </div>
          <div className="flex-shrink-0 text-right">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>
        {taskDescription && (
          <div className="mt-2">
            { /* Only show toggle button if description is actually truncated */ }
            {taskDescription.length > 120 && (
              <button
                type="button"
                className="text-xs text-blue-600 hover:underline"
                onClick={(e) => { e.stopPropagation(); setShowFullDescription(!showFullDescription); }}
              >
                {showFullDescription ? 'Hide full description' : 'Show full description'}
              </button>
            )}
            {!showFullDescription && taskDescription !== (shortName || taskDescription) && (
              <div className="text-xs text-gray-700 mt-1">
                {taskDescription.length > 120
                  ? `${taskDescription.slice(0, 117)}...`
                  : taskDescription}
              </div>
            )}
            {showFullDescription && (
              <pre className="bg-gray-100 p-2 rounded text-xs text-gray-700 mt-1 whitespace-pre-wrap break-words max-h-40 overflow-auto">
                <code>{taskDescription}</code>
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
