import React, { useState } from 'react';
import type { TaskExecution } from '../../types/trace';

interface TimelineItemProps {
  item: TaskExecution;
  onItemClick: (task: TaskExecution) => void;
  isNew?: boolean;
  isCurrentlyExecuting?: boolean;
}

export const TimelineItem: React.FC<TimelineItemProps> = ({
  item,
  onItemClick,
  isNew = false,
  isCurrentlyExecuting = false,
}) => {
  const [showFullDescription, setShowFullDescription] = useState(false);
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

  const PHASE_DEFS: Array<{ key: keyof TaskExecution['phases']; label: string }> = [
    { key: 'sop_resolution', label: 'Sop Resolution' },
    { key: 'task_creation', label: 'Task Creation' },
    { key: 'task_execution', label: 'Task Execution' },
    { key: 'context_update', label: 'Context Update' },
    { key: 'new_task_generation', label: 'New Task Generation' },
  ];

  const handleItemClick = () => {
    onItemClick(item);
  };

  const phases = PHASE_DEFS.map(def => {
    const phase = item.phases?.[def.key as keyof typeof item.phases];
    const status = phase?.status ?? 'pending';
    const completed = status === 'completed';
    // Use green for completed; grey for all others to keep it intuitive and compact
    const chipClass = completed ? getStatusBadgeColor('completed') : 'bg-gray-100 text-gray-800';
    const phaseDuration = phase ? calculateDuration(phase.start_time, phase.end_time) : '';
    return { label: def.label, status, chipClass, completed, duration: phaseDuration };
  });
  const isCompleted = item.status === 'completed';
  const duration = calculateDuration(item.start_time, item.end_time);

  const cardBaseClasses = "border rounded-lg p-3 shadow-sm transition-all duration-200 hover:shadow-md cursor-pointer";
  const animationClass = isNew ? 'animate-slide-in-and-fade' : '';
  const currentlyExecutingClass = isCurrentlyExecuting ? 'animate-pulse-border' : '';
  const statusColor = isCurrentlyExecuting && item.status === 'completed'
    ? getStatusColor('running') // Show as "running" if it's the last completed task
    : getStatusColor(item.status);

  const shouldShowStatusBadge = !(isCurrentlyExecuting && item.status === 'completed');

  const titleText = item.short_name || (item.phases?.task_creation?.created_task?.short_name) || item.task_description || `Task ${item.task_execution_counter}`;
  const fullDescription = item.task_description;

  return (
    <div className="relative">
      <div
        className={`${cardBaseClasses} ${statusColor} ${animationClass} ${currentlyExecutingClass}`}
        onClick={handleItemClick}
      >
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-gray-900 truncate" title={titleText}>
              {titleText}
            </h3>
          </div>
          <div className="ml-2 flex-shrink-0 flex items-center space-x-2">
            {shouldShowStatusBadge && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(item.status)}`}>
                {item.status}
              </span>
            )}
            {isCurrentlyExecuting && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Executing
              </span>
            )}
          </div>
        </div>

        {fullDescription && (
          <div className="mt-2">
            <button
              type="button"
              className="text-xs text-blue-600 hover:underline"
              onClick={(e) => { e.stopPropagation(); setShowFullDescription(!showFullDescription); }}
            >
              {showFullDescription ? 'Hide full description' : 'Show full description'}
            </button>
            {showFullDescription && (
              <pre className="bg-gray-100 p-2 rounded text-xs text-gray-700 mt-1 whitespace-pre-wrap break-words max-h-40 overflow-auto">
                <code>{fullDescription}</code>
              </pre>
            )}
          </div>
        )}

        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-600 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
            <div>
              {isCompleted ? (
                <>
                  <span className="font-medium">Duration:</span> {duration}
                </>
              ) : (
                <>
                  <span className="font-medium">Started:</span> {formatTime(item.start_time)}
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {phases.map((phase, idx) => (
                <span
                  key={idx}
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${phase.chipClass}`}
                >
                  {phase.label}
                  {phase.completed && (
                    <>
                      <span className="ml-1" aria-label="completed">✔</span>
                      {phase.duration && phase.duration !== 'N/A' && (
                        <span className="ml-1">({phase.duration})</span>
                      )}
                    </>
                  )}
                </span>
              ))}
            </div>
          </div>
        </div>

        


        {item.error && (
          <div className="mt-2">
            <h4 className="text-xs font-medium text-red-600 mb-1">Error</h4>
            <pre className="bg-red-50 p-2 rounded text-xs text-red-700 max-h-24 overflow-auto whitespace-pre-wrap break-all">
              <code>{item.error}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
