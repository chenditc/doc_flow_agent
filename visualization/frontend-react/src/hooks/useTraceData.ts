/**
 * Custom hook for fetching and managing trace data with React Query
 */

import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { traceService } from '../services/traceService';
import { useTraceContext } from '../context';

// Query keys
export const traceQueryKeys = {
  all: ['traces'] as const,
  lists: () => [...traceQueryKeys.all, 'list'] as const,
  list: (filters?: any) => [...traceQueryKeys.lists(), filters] as const,
  details: () => [...traceQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...traceQueryKeys.details(), id] as const,
  latest: () => [...traceQueryKeys.all, 'latest'] as const,
  statistics: (id: string) => [...traceQueryKeys.all, 'statistics', id] as const,
};

/**
 * Hook to fetch list of available traces
 */
export const useTraces = () => {
  const { setAvailableTraces, setError } = useTraceContext();

  return useQuery({
    queryKey: traceQueryKeys.lists(),
    queryFn: async () => {
      try {
        const traces = await traceService.getTraces();
        setAvailableTraces(traces);
        setError(null);
        return traces;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch traces';
        setError(errorMessage);
        throw error;
      }
    },
    staleTime: 30000, // 30 seconds
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};

/**
 * Hook to fetch a specific trace by ID
 */
export const useTrace = (traceId: string | null) => {
  const { setCurrentTrace, setError, setLoadingTrace } = useTraceContext();

  return useQuery({
    queryKey: traceQueryKeys.detail(traceId || ''),
    queryFn: async () => {
      if (!traceId) {
        throw new Error('Trace ID is required');
      }

      try {
        setLoadingTrace(true);
        const trace = await traceService.getTrace(traceId);
        setCurrentTrace(trace);
        setError(null);
        return trace;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : `Failed to fetch trace ${traceId}`;
        setError(errorMessage);
        setCurrentTrace(null);
        throw error;
      } finally {
        setLoadingTrace(false);
      }
    },
    enabled: !!traceId,
    staleTime: 10000, // 10 seconds
    retry: (failureCount, error) => {
      // Don't retry if trace doesn't exist (404-like errors)
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
};

/**
 * Hook to fetch the latest trace
 */
export const useLatestTrace = () => {
  const { setError } = useTraceContext();

  return useQuery({
    queryKey: traceQueryKeys.latest(),
    queryFn: async () => {
      try {
        const latestTraceId = await traceService.getLatestTrace();
        setError(null);
        return latestTraceId;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch latest trace';
        setError(errorMessage);
        throw error;
      }
    },
    staleTime: 5000, // 5 seconds
    retry: 3,
  });
};

/**
 * Hook to fetch trace statistics
 */
export const useTraceStatistics = (traceId: string | null) => {
  return useQuery({
    queryKey: traceQueryKeys.statistics(traceId || ''),
    queryFn: async () => {
      if (!traceId) {
        throw new Error('Trace ID is required');
      }
      return traceService.getTraceStatistics(traceId);
    },
    enabled: !!traceId,
    staleTime: 60000, // 1 minute
    retry: 2,
  });
};

/**
 * Hook for manually refreshing trace data
 */
export const useRefreshTrace = () => {
  const queryClient = useQueryClient();
  const { state } = useTraceContext();

  return useMutation({
    mutationFn: async (traceId?: string) => {
      const targetTraceId = traceId || state.selectedTraceId;
      if (!targetTraceId) {
        throw new Error('No trace ID provided for refresh');
      }

      // Invalidate and refetch the specific trace
      await queryClient.invalidateQueries({
        queryKey: traceQueryKeys.detail(targetTraceId),
      });

      // Also invalidate statistics if they exist
      await queryClient.invalidateQueries({
        queryKey: traceQueryKeys.statistics(targetTraceId),
      });

      return targetTraceId;
    },
    onSuccess: (traceId) => {
      console.log(`Successfully refreshed trace: ${traceId}`);
    },
    onError: (error) => {
      console.error('Failed to refresh trace:', error);
    },
  });
};

/**
 * Hook for auto-refreshing trace data at intervals
 */
export const useAutoRefresh = (enabled: boolean, intervalMs = 5000) => {
  const { state } = useTraceContext();
  const refreshTrace = useRefreshTrace();

  const intervalRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    if (enabled && state.selectedTraceId && !state.isRealTimeEnabled) {
      // Only auto-refresh if not using real-time monitoring
      intervalRef.current = setInterval(() => {
        refreshTrace.mutate(undefined);
      }, intervalMs);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, state.selectedTraceId, state.isRealTimeEnabled, intervalMs, refreshTrace]);

  return {
    isAutoRefreshing: enabled && !!state.selectedTraceId && !state.isRealTimeEnabled,
    stopAutoRefresh: () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    },
  };
};

/**
 * Hook to check if a trace exists
 */
export const useTraceExists = (traceId: string | null) => {
  return useQuery({
    queryKey: ['trace-exists', traceId],
    queryFn: async () => {
      if (!traceId) return false;
      return traceService.traceExists(traceId);
    },
    enabled: !!traceId,
    staleTime: 30000, // 30 seconds
    retry: 1,
  });
};

// Re-export React for the hooks
import React from 'react';
