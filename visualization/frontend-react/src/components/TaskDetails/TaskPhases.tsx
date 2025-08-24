import React, { useState } from 'react';
import type { TaskExecution, TaskPhases as TaskPhasesType } from '../../types/trace';
import { SOPResolutionViewer } from '../SOPResolution/SOPResolutionViewer';
import { TaskCreationPhaseViewer } from '../enhanced/TaskCreationPhaseViewer';

interface TaskPhasesProps {
  task: TaskExecution;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({ 
  title, 
  children, 
  defaultExpanded = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border rounded-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:bg-gray-100 transition-colors border-b border-gray-200 rounded-t-md"
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">{title}</span>
          <svg
            className={`h-5 w-5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      
      {isExpanded && (
        <div className="p-4">
          {children}
        </div>
      )}
    </div>
  );
};

export const TaskPhases: React.FC<TaskPhasesProps> = ({ task }) => {
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
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'started':
        return 'bg-blue-100 text-blue-800';
      case 'interrupted':
        return 'bg-yellow-100 text-yellow-800';
      case 'retrying':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatPhaseName = (phaseName: string): string => {
    return phaseName
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  const stripMetaFields = (phaseData: any) => {
    if (!phaseData || typeof phaseData !== 'object') return {};
    
    const { start_time, end_time, status, ...rest } = phaseData;
    return rest;
  };

  const phases = task.phases || {};
  const phaseNames = Object.keys(phases);

  if (phaseNames.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-4 text-sm font-medium text-gray-900">No phase information</h3>
        <p className="mt-2 text-sm text-gray-500">
          This task execution doesn't have detailed phase information available.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Execution Phases</h3>
      
      <div className="space-y-3">
        {phaseNames.map((phaseName) => {
          const phaseData = phases[phaseName as keyof TaskPhasesType];
          if (!phaseData) return null;

          // Special handling for SOP resolution phase
          if (phaseName === 'sop_resolution' && 'input' in phaseData) {
            return (
              <div key={phaseName} className="border rounded-md">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-md">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-900">SOP Resolution</span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
                        {phaseData.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
                      ({calculateDuration(phaseData.start_time, phaseData.end_time)})
                    </div>
                  </div>
                </div>
                <CollapsibleSection title="View Details" defaultExpanded={false}>
                  <SOPResolutionViewer phaseData={phaseData} />
                </CollapsibleSection>
              </div>
            );
          }

          // Special handling for task creation phase
          if (phaseName === 'task_creation' && 'sop_document' in phaseData) {
            return (
              <div key={phaseName} className="border rounded-md">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-md">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-900">Task Creation</span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
                        {phaseData.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
                      ({calculateDuration(phaseData.start_time, phaseData.end_time)})
                    </div>
                  </div>
                </div>
                <CollapsibleSection title="View Details" defaultExpanded={false}>
                  <TaskCreationPhaseViewer phaseData={phaseData} />
                </CollapsibleSection>
              </div>
            );
          }

          // Generic phase handling
          const detailsData = stripMetaFields(phaseData);
          const hasDetails = Object.keys(detailsData).length > 0;

          return (
            <div key={phaseName} className="border rounded-md">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-gray-900">{formatPhaseName(phaseName)}</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
                      {phaseData.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
                    ({calculateDuration(phaseData.start_time, phaseData.end_time)})
                  </div>
                </div>
              </div>

              {hasDetails && (
                <CollapsibleSection title="View Details (JSON)" defaultExpanded={false}>
                  <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
                    {JSON.stringify(detailsData, null, 2)}
                  </pre>
                </CollapsibleSection>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
