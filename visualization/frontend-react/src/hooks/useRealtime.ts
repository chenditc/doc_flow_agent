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
  console.warn('[useRealtime] Cannot start monitoring: no trace ID provided');
      return false;
    }

    try {
  console.log('[useRealtime] startMonitoring called with traceId:', targetTraceId);
      realtimeService.startMonitoring(targetTraceId);
      setRealTimeEnabled(true);
      return true;
    } catch (error) {
  console.error('[useRealtime] Failed to start monitoring:', error);
      setConnectionState(false, error instanceof Error ? error.message : 'Unknown error');
      return false;
    }
  }, [state.selectedTraceId, realtimeService, setRealTimeEnabled, setConnectionState]);

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
  console.log('[useRealtime] stopMonitoring called');
    realtimeService.stopMonitoring();
    setRealTimeEnabled(false);
  }, [realtimeService, setRealTimeEnabled]);

  // Toggle monitoring
  const toggleMonitoring = useCallback(() => {
  console.log('[useRealtime] toggleMonitoring. isRealTimeEnabled:', state.isRealTimeEnabled, 'selectedTraceId:', state.selectedTraceId);
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
        console.log('[useRealtime] onMessage received:', message);
        setLastUpdate(new Date().toISOString());
        
        // Trigger a trace refresh when we receive updates
        if (state.selectedTraceId) {
          console.log('[useRealtime] refreshing trace due to realtime message. traceId:', state.selectedTraceId);
          refreshTrace.mutate(state.selectedTraceId);
        }
        
        // Call user-provided callback
        if (optionsRef.current.onMessage) {
          optionsRef.current.onMessage(message);
        }
      },
      onError: (error) => {
  console.log('[useRealtime] onError:', error);
        setConnectionState(false, error.message);
        
        // Call user-provided callback
        if (optionsRef.current.onError) {
          optionsRef.current.onError(error);
        }
      },
      onOpen: () => {
  console.log('[useRealtime] onOpen');
        setConnectionState(true, null);
        
        if (optionsRef.current.onConnectionChange) {
          optionsRef.current.onConnectionChange(true);
        }
      },
      onClose: () => {
  console.log('[useRealtime] onClose');
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

  // Auto-restart monitoring when trace changes (but not when first enabling)
  const prevTraceIdRef = useRef<string | null>(null);
  const prevIsEnabledRef = useRef<boolean>(false);
  
  useEffect(() => {
    if (state.isRealTimeEnabled && state.selectedTraceId) {
      const traceChanged = prevTraceIdRef.current && prevTraceIdRef.current !== state.selectedTraceId;
      const wasAlreadyEnabled = prevIsEnabledRef.current;
      
      // Only restart if trace changed while monitoring was already active
      if (traceChanged && wasAlreadyEnabled) {
    console.log('[useRealtime] Trace changed from', prevTraceIdRef.current, 'to', state.selectedTraceId, 'restarting monitoring');
        realtimeService.stopMonitoring();
        setTimeout(() => {
          realtimeService.startMonitoring(state.selectedTraceId!);
        }, 100); // Small delay to ensure cleanup
      }
    }
    
    // Update refs for next render
  console.log('[useRealtime] Trace/Enabled state changed. selectedTraceId:', state.selectedTraceId, 'isRealTimeEnabled:', state.isRealTimeEnabled);
    prevTraceIdRef.current = state.selectedTraceId;
    prevIsEnabledRef.current = state.isRealTimeEnabled;
  }, [state.selectedTraceId, state.isRealTimeEnabled, realtimeService]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
  console.log('[useRealtime] cleanup: stopMonitoring');
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
