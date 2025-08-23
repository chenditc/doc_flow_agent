import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';
import { RealtimeToggle } from '../common/ConnectionIndicators';
import { useRealtime } from '../../hooks/useRealtime';
import { traceService } from '../../services/traceService';

interface TraceSelectorProps {
  selectedTraceId: string | null;
  onTraceSelected: (traceId: string | null) => void;
  isLoading?: boolean;
}

export const TraceSelector: React.FC<TraceSelectorProps> = ({
  selectedTraceId,
  onTraceSelected,
  isLoading = false
}) => {
  const [autoSelectLatest, setAutoSelectLatest] = useState(true);
  
  // Fetch available traces
  const {
    data: traces = [],
    isLoading: tracesLoading,
    error: tracesError,
    refetch: refetchTraces
  } = useQuery({
    queryKey: ['traces'],
    queryFn: () => traceService.getTraces(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Real-time functionality
  const {
    isEnabled: realtimeEnabled,
    isConnected: realtimeConnected,
    startMonitoring,
    stopMonitoring,
  } = useRealtime();

  // Auto-select latest trace when traces load
  useEffect(() => {
    if (autoSelectLatest && traces.length > 0 && !selectedTraceId) {
      const latest = [...traces].sort().reverse()[0];
      onTraceSelected(latest);
      setAutoSelectLatest(false);
    }
  }, [traces, selectedTraceId, autoSelectLatest, onTraceSelected]);

  const handleTraceChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const traceId = event.target.value || null;
    onTraceSelected(traceId);
  };

  const handleRealtimeToggle = (enabled: boolean) => {
  console.log('[TraceSelector] Realtime toggle to', enabled, 'for traceId:', selectedTraceId);
    if (enabled && selectedTraceId) {
      startMonitoring(selectedTraceId);
    } else {
      stopMonitoring();
    }
  };

  const handleRefresh = () => {
    refetchTraces();
  };

  const formatTraceDisplayName = (traceId: string): string => {
    return traceId
      .replace(/^session_/, '')
      .replace(/_/g, ' - ');
  };

  if (tracesLoading) {
    return <LoadingSpinner size="medium" message="Loading traces..." />;
  }

  if (tracesError) {
    return (
      <ErrorMessage
        title="Failed to load traces"
        message={tracesError instanceof Error ? tracesError.message : 'Unknown error occurred'}
        onRetry={handleRefresh}
        retryText="Refresh"
      />
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Trace selection */}
        <div className="flex-1 min-w-0">
          <label htmlFor="trace-select" className="block text-sm font-medium text-gray-700 mb-1">
            Select Trace
          </label>
          <div className="flex gap-2">
            <select
              id="trace-select"
              value={selectedTraceId || ''}
              onChange={handleTraceChange}
              disabled={isLoading}
              className="flex-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500"
            >
              <option value="">Select a trace...</option>
              {traces
                .slice()
                .sort()
                .reverse()
                .map((traceId) => (
                  <option key={traceId} value={traceId}>
                    {formatTraceDisplayName(traceId)}
                  </option>
                ))}
            </select>
            
            <button
              onClick={handleRefresh}
              disabled={tracesLoading || isLoading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh traces"
            >
              <svg 
                className={`h-4 w-4 ${tracesLoading ? 'animate-spin' : ''}`} 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Real-time toggle */}
        {selectedTraceId && (
          <div className="flex-shrink-0">
            <RealtimeToggle
              isEnabled={realtimeEnabled}
              isConnected={realtimeConnected}
              onToggle={() => handleRealtimeToggle(!realtimeEnabled)}
              disabled={isLoading}
            />
          </div>
        )}
      </div>

      {/* Trace info */}
      {selectedTraceId && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="text-xs text-gray-500">
            Selected: <span className="font-mono text-gray-700">{selectedTraceId}</span>
          </div>
        </div>
      )}
    </div>
  );
};
