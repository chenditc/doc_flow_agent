/**
 * Custom hook for managing real-time connections and updates
 */

import React, { useCallback, useEffect, useRef } from 'react';
import { useTraceContext } from '../context';
import { useRefreshTrace } from './useTraceData';

export interface UseRealtimeOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: any) => void;
  onError?: (error: Error) => void;
  onConnectionChange?: (isConnected: boolean) => void;
}

/**
 * Hook for managing real-time trace monitoring
 */
export const useRealtime = (options: UseRealtimeOptions = {}) => {
  const {
    state,
    realtimeService,
    setRealTimeEnabled,
    setConnectionState,
    setLastUpdate,
  } = useTraceContext();

  const refreshTrace = useRefreshTrace();
  const optionsRef = useRef(options);

  // Update options ref when props change
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  // Start monitoring for the current trace
  const startMonitoring = useCallback((traceId?: string) => {
    const targetTraceId = traceId || state.selectedTraceId;
    if (!targetTraceId) {
      console.warn('Cannot start monitoring: no trace ID provided');
      return false;
    }

    try {
      realtimeService.startMonitoring(targetTraceId);
      setRealTimeEnabled(true);
      return true;
    } catch (error) {
      console.error('Failed to start monitoring:', error);
      setConnectionState(false, error instanceof Error ? error.message : 'Unknown error');
      return false;
    }
  }, [state.selectedTraceId, realtimeService, setRealTimeEnabled, setConnectionState]);

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    realtimeService.stopMonitoring();
    setRealTimeEnabled(false);
  }, [realtimeService, setRealTimeEnabled]);

  // Toggle monitoring
  const toggleMonitoring = useCallback(() => {
    if (state.isRealTimeEnabled) {
      stopMonitoring();
      return false;
    } else {
      return startMonitoring();
    }
  }, [state.isRealTimeEnabled, startMonitoring, stopMonitoring]);

  // Check connection status
  const getConnectionStatus = useCallback(() => {
    return realtimeService.getConnectionState();
  }, [realtimeService]);

  // Update realtime service options when they change
  useEffect(() => {
    realtimeService.updateOptions({
      onMessage: (message) => {
        setLastUpdate(new Date().toISOString());
        
        // Trigger a trace refresh when we receive updates
        if (state.selectedTraceId) {
          refreshTrace.mutate(state.selectedTraceId);
        }
        
        // Call user-provided callback
        if (optionsRef.current.onMessage) {
          optionsRef.current.onMessage(message);
        }
      },
      onError: (error) => {
        setConnectionState(false, error.message);
        
        // Call user-provided callback
        if (optionsRef.current.onError) {
          optionsRef.current.onError(error);
        }
      },
      onOpen: () => {
        setConnectionState(true, null);
        
        if (optionsRef.current.onConnectionChange) {
          optionsRef.current.onConnectionChange(true);
        }
      },
      onClose: () => {
        setConnectionState(false, null);
        
        if (optionsRef.current.onConnectionChange) {
          optionsRef.current.onConnectionChange(false);
        }
      },
      reconnectInterval: options.reconnectInterval,
      maxReconnectAttempts: options.maxReconnectAttempts,
    });
  }, [
    realtimeService,
    setConnectionState,
    setLastUpdate,
    refreshTrace,
    state.selectedTraceId,
    options.reconnectInterval,
    options.maxReconnectAttempts,
  ]);

  // Auto-restart monitoring when trace changes
  useEffect(() => {
    if (state.isRealTimeEnabled && state.selectedTraceId) {
      // Stop current monitoring and restart with new trace
      realtimeService.stopMonitoring();
      setTimeout(() => {
        realtimeService.startMonitoring(state.selectedTraceId!);
      }, 100); // Small delay to ensure cleanup
    }
  }, [state.selectedTraceId, state.isRealTimeEnabled, realtimeService]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      realtimeService.stopMonitoring();
    };
  }, [realtimeService]);

  return {
    // State
    isEnabled: state.isRealTimeEnabled,
    isConnected: state.isConnected,
    connectionError: state.connectionError,
    lastUpdate: state.lastUpdate,
    connectionStatus: getConnectionStatus(),
    
    // Actions
    startMonitoring,
    stopMonitoring,
    toggleMonitoring,
    
    // Utils
    canMonitor: !!state.selectedTraceId,
    isMonitoring: state.isRealTimeEnabled && state.isConnected,
  };
};

/**
 * Hook for monitoring connection health and auto-reconnection
 */
export const useConnectionHealth = () => {
  const { state, realtimeService } = useTraceContext();
  const [healthStatus, setHealthStatus] = React.useState<'healthy' | 'degraded' | 'error'>('healthy');
  const [lastHealthCheck, setLastHealthCheck] = React.useState<string | null>(null);
  
  const healthCheckInterval = useRef<NodeJS.Timeout | null>(null);

  const checkHealth = useCallback(async () => {
    if (!state.isRealTimeEnabled || !state.selectedTraceId) {
      setHealthStatus('healthy');
      return;
    }

    const connectionState = realtimeService.getConnectionState();
    const now = new Date().toISOString();
    
    setLastHealthCheck(now);

    if (connectionState === 'open' && state.isConnected) {
      setHealthStatus('healthy');
    } else if (connectionState === 'connecting' || connectionState === 'closed') {
      setHealthStatus('degraded');
    } else {
      setHealthStatus('error');
    }
  }, [state.isRealTimeEnabled, state.selectedTraceId, state.isConnected, realtimeService]);

  // Periodic health checks
  useEffect(() => {
    if (state.isRealTimeEnabled) {
      // Initial check
      checkHealth();
      
      // Set up periodic checks
      healthCheckInterval.current = setInterval(checkHealth, 10000); // Every 10 seconds
    } else {
      setHealthStatus('healthy');
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current);
        healthCheckInterval.current = null;
      }
    }

    return () => {
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current);
        healthCheckInterval.current = null;
      }
    };
  }, [state.isRealTimeEnabled, checkHealth]);

  return {
    healthStatus,
    lastHealthCheck,
    checkHealth,
  };
};
